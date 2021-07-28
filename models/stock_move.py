import json
import time

from itertools import groupby
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from operator import itemgetter

class StockMove(models.Model):
    _inherit = 'stock.move'

    saled_qty = fields.Float(
        string='Saled qty',
        required=False,default=0)

    def valid_move(self):
        vals=self.env['stock.move'].search([
            ('product_id','=',self.product_id.id),
            ('location_dest_id','=',self.location_id.id),
            ('product_qty','>',0),
            ('state','in',['done','confirmed']),
            ('date','>=','2020-01-01 00:00:00')
        ], order='date asc')
        return vals

    def linkedPurchase(self):
        view = self.env.ref('picking_purchase_order.purchase_qty_form_view')
        # wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
        lst_move = self.valid_move()
        contxt = {'product_id': self.product_id.id,'location_id':self.location_dest_id.id,'product_uom':self.product_uom.id,'deliv_qty':self.reserved_availability,'move_id':self.id}

        wiz = self.env['purchase.quantity'].create(contxt)
        for rec in lst_move:
            data={
                'purchaseqty_id':wiz.id,
                'picking_id':self.picking_id.id,
                'product_id':rec.product_id.id,
                'location_dest_id':rec.location_dest_id.id,
                'product_qty':rec.product_qty,
                'saled_qty':rec.saled_qty,
                'move_id':rec.id,
                'purchase_line_id':rec.purchase_line_id.id,
                'available_qty':rec.product_qty-rec.saled_qty
            }
            rec.env['purchase.quantity.line'].create(data)

        return {
            'name': _('Purchase quantity'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.quantity',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': wiz.id,
            'context':contxt #self.env.context,
        }

    def action_show_details(self):
        pick_type=self.picking_id.picking_type_id
        if pick_type.name in('Delivery Orders','Livraisons'):
            return self.linkedPurchase()
        else:

            """ Returns an action that will open a form view (in a popup) allowing to work on all the
            move lines of a particular move. This form view is used when "show operations" is not
            checked on the picking type.
            """
            self.ensure_one()

            # If "show suggestions" is not checked on the picking type, we have to filter out the
            # reserved move lines. We do this by displaying `move_line_nosuggest_ids`. We use
            # different views to display one field or another so that the webclient doesn't have to
            # fetch both.
            if self.picking_id.picking_type_id.show_reserved:
                view = self.env.ref('stock.view_stock_move_operations')
            else:
                view = self.env.ref('stock.view_stock_move_nosuggest_operations')

            picking_type_id = self.picking_type_id or self.picking_id.picking_type_id
            return {
                'name': _('Detailed Operations'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.move',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': self.id,
                'context': dict(
                    self.env.context,
                    show_lots_m2o=self.has_tracking != 'none' and (picking_type_id.use_existing_lots or self.state == 'done' or self.origin_returned_move_id.id),  # able to create lots, whatever the value of ` use_create_lots`.
                    show_lots_text=self.has_tracking != 'none' and picking_type_id.use_create_lots and not picking_type_id.use_existing_lots and self.state != 'done' and not self.origin_returned_move_id.id,
                    show_source_location=self.location_id.child_ids,
                    show_destination_location=self.location_dest_id.child_ids,
                    show_package=not self.location_id.usage == 'supplier',
                    show_reserved_quantity=self.state != 'done'
                ),
            }



class StockPicking(models.Model):
    _inherit='stock.picking'

    details_ids = fields.One2many(
        comodel_name='purchase.quantity.line',
        inverse_name='picking_id',
        string='Related Purchase',
        required=False)

    def generateSaleFromPurchase(self):
        for move in self.move_lines:
            qty_move=move.quantity_done
            lst_move=move.valid_move()
            print(lst_move)
            if lst_move:
                for rec in lst_move:
                    print(qty_move)
                    if qty_move==0:
                        return
                    if (rec.product_qty - rec.saled_qty) <= 0:
                        qty_move = 0
                        return

                    if qty_move <= (rec.product_qty - rec.saled_qty):
                        # create a line and exit this product
                        self.env['purchase.picking.sale'].create({
                            'move_id': rec.id,
                            'product_qty': qty_move,
                            'product_uom_qty': qty_move,
                            'picking_id': move.picking_id.id,
                        })
                        qty = rec.saled_qty + qty_move
                        rec.write({'saled_qty': qty})
                        qty_move = 0
                    else:
                        # create and return for new record
                        self.env['purchase.picking.sale'].create({
                            'move_id': rec.id,
                            'product_qty': qty_move,
                            'product_uom_qty': qty_move,
                            'date_move': move.date,
                            'picking_id': move.picking_id.id,
                        })
                        qty = rec.saled_qty + qty_move
                        rec.write({'saled_qty': qty})
                        qty_move = qty_move - (rec.product_qty - rec.saled_qty)

    @api.multi
    def button_validate(self):
        self.ensure_one()
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some lines to move'))

        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                                 self.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
        no_reserved_quantities = all(
            float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in
            self.move_line_ids)
        if no_reserved_quantities and no_quantities_done:
            raise UserError(_('You cannot validate a transfer if you have not processed any quantity. You should rather cancel the transfer.'))

        if picking_type.use_create_lots or picking_type.use_existing_lots:
            lines_to_check = self.move_line_ids
            if not no_quantities_done:
                lines_to_check = lines_to_check.filtered(
                    lambda line: float_compare(line.qty_done, 0,
                                               precision_rounding=line.product_uom_id.rounding)
                )

            for line in lines_to_check:
                product = line.product_id
                if product and product.tracking != 'none':
                    if not line.lot_name and not line.lot_id:
                        raise UserError(_('You need to supply a lot/serial number for %s.') % product.display_name)

        if no_quantities_done:
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
            view = self.env.ref('stock.view_overprocessed_transfer')
            wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.overprocessed.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        # Check backorder should check for other barcodes
        # for rec in self.move_lines:
        #     return rec.linkedPurchase()

        if self._check_backorder():
            return self.action_generate_backorder_wizard()
        self.action_done()
        return



class DeliveryPurchase(models.Model):
    _name="purchase.picking.sale"

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=False,related='move_id.product_id')

    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Location_id',
        required=False,related='move_id.location_id')
    
    product_qty = fields.Float(
        string='Qty', 
        required=False)

    product_uom_qty = fields.Float(
        string='Qty uom',
        required=False)
    
    product_uom = fields.Many2one(
        comodel_name='product.uom',
        string='Unit of mesure',
        required=False,related='move_id.product_uom')
    
    date_move = fields.Datetime(
        string='Date',
        required=False)

    origin=fields.Char(
        string='Origin',
        required=False,related='move_id.origin')

    origin_date = fields.Datetime(
        string='Date',
        required=False, related='move_id.date')

    origin_reference = fields.Char(
        string='Reference',
        required=False, related='move_id.reference')

    move_id = fields.Many2one(
        comodel_name='stock.move',
        string='Move_id',
        required=False)

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Mouvement',
        required=False)












