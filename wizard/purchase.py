from odoo import fields, models, api
from odoo.exceptions import except_orm, Warning, RedirectWarning
class PurchaseQty(models.Model):
    _name = 'purchase.quantity'

    move_id = fields.Many2one(
        comodel_name='stock.move',
        string='Move',
        required=False)

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=False,readonly=True)

    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Location',
        required=False,readonly=True)

    deliv_qty = fields.Float(
        string='Delivered qty',
        required=False,readonly=True)

    product_uom = fields.Many2one(
        comodel_name='product.uom',
        string='Unit of mesure',
        required=False,readonly=True)

    lst_move = fields.One2many(
        comodel_name='purchase.quantity.line',
        inverse_name='purchaseqty_id',
        string=' lst_move',
        required=False)
    
    total_amount = fields.Float(
        string='Total amount',
        required=False)

    def check_quantity(self):
        qty_move = self.deliv_qty
        for rec in self.lst_move:
            if qty_move == 0:
                return
            if (rec.product_qty - rec.saled_qty) <= 0:
                qty_move = 0
                return
            if qty_move <= (rec.product_qty - rec.saled_qty):
                qty = rec.saled_qty + qty_move
                rec.new_qty= qty
                qty_move = 0
            else:
                qty = rec.saled_qty + qty_move
                rec.new_qty=qty
                qty_move = qty_move - (rec.product_qty - rec.saled_qty)

    @api.onchange('lst_move')
    def calculamount(self):
        mnt=0
        for rec in self.lst_move:
            mnt=mnt+(rec.new_qty*rec.unit_price)
            rec.available_qty = rec.product_qty - rec.saled_qty - rec.new_qty
            rec.amount_line=rec.new_qty*rec.unit_price

        self.total_amount=mnt

    def getTotalQty(self):
        qty=0
        for rec in self.lst_move:
            qty = qty + rec.new_qty
        return qty

    def setcostmove(self):
        mov=self.env['stock.move'].search([('id','=',self.move_id.id)])
        if mov:
            mov.write({
                'price_unit':-self.total_amount/self.deliv_qty,
                'value':-self.total_amount,
                'remaining_qty':-self.deliv_qty,
                'quantity_done':self.deliv_qty,
                'remaining_value':-self.total_amount
            })

    def confirmStockPicking(self):
        sp=self.env['stock.picking'].search([('id','=',self.move_id.picking_id.id)])
        if sp._check_backorder():
            return sp.action_generate_backorder_wizard()
        sp.action_done()

    @api.multi
    def write(self, vals):
        print(vals)
        res = super(PurchaseQty, self).write(vals)
        qty=self.getTotalQty()
        if qty!=self.deliv_qty:
            for rec in self.lst_move:
                rec.write({'available_qty':rec.available_qty+rec.new_qty,'new_qty':0})
            raise Warning('quantity not valide')
            return False
        else:
            for elm in self.lst_move:
                if elm.new_qty==0:
                    elm.unlink()
                else:
                    mv=self.env['stock.move'].search([('id','=',elm.move_id.id)])
                    if mv:
                        mv.write({'saled_qty':mv.saled_qty+elm.new_qty})
            self.setcostmove()
            self.confirmStockPicking()
            return True

class PurchaseQtyLine(models.Model):
    _name='purchase.quantity.line'

    purchaseqty_id = fields.Many2one(
        comodel_name='purchase.quantity',
        string='purchase',
        required=False,readonly=True)

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=False,readonly=True)

    location_dest_id = fields.Many2one(
        comodel_name='stock.location',
        string='Location',
        required=False,readonly=True)

    product_qty = fields.Float(
        string='Qty',
        required=False,readonly=True)

    saled_qty = fields.Float(
        string='Delivred qty',
        required=False,readonly=True)

    move_id = fields.Many2one(
        comodel_name='stock.move',
        string='move',
        required=False,readonly=True)

    purchase_line_id= fields.Many2one(
        comodel_name='purchase.order.line',
        string='purchase_line_id',
        required=False,readonly=True)

    origin = fields.Char(
        string='Origin',
        required=False,related='move_id.origin')

    available_qty = fields.Float(
        string='Available qty',
        required=False,readonly=True)

    new_qty = fields.Float(
        string='New qty',
        required=False)
    
    unit_price = fields.Float(
        string='unit price', 
        required=False,related='purchase_line_id.price_unit',readonly=True)

    amount_line = fields.Float(
        string='Amount',
        required=False,)

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Mouvement',
        required=False)
