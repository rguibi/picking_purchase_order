from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def action_view_picking(self):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        '''
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]

        # override the context to get rid of the default filtering on operation type
        result['context'] = {}
        pick_ids = self.mapped('picking_ids')
        for rec in pick_ids:
            if not rec.scheduled_date:
                rec.write({'scheduled_date': self.date_order})
        # choose the view_mode accordingly
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids.id
        return result
