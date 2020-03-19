# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    payment_ids = fields.One2many('account.payment', 'purchase_id', 'Payments')
    payment_count = fields.Integer(compute="_compute_payment", string='Payment Count', copy=False, default=0,
                                   store=True)
    l10n_in_journal_id = fields.Many2one('account.journal', string="Journal", \
                                         states={'posted': [('readonly', True)]}, domain="[('type','=', 'purchase')]")

    @api.depends('payment_ids')
    def _compute_payment(self):
        for order in self:
            order.payment_count = len(order.payment_ids)

    def action_view_payment(self):
        '''
            This function returns an action that display existing payments of given purchase order ids.
            When only one found, show the payments immediately.
        '''
        action = self.env.ref('account.action_account_payments_payable')
        result = action.read()[0]
        create_payment = self.env.context.get('create_payment', False)
        # override the context to get rid of the default filtering
        result['context'] = {
            'default_payment_type': 'outbound',
            'default_partner_type': 'supplier',
            'search_default_outbound_filter': 1,
            'res_partner_search_mode': 'supplier',
            'default_company_id': self.company_id.id,
            'default_purchase_id': self.id,
            'default_partner_id': self.partner_id.id,
        }
        # choose the view_mode accordingly
        if len(self.payment_ids) > 1 and not create_payment:
            result['domain'] = "[('id', 'in', " + str(self.payment_ids.ids) + ")]"
        else:
            res = self.env.ref('account.view_account_payment_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                result['views'] = form_view
            # if we want to create a new payment.
            if not create_payment:
                result['res_id'] = self.payment_ids.id or False
        result['context']['default_origin'] = self.name
        result['context']['default_reference'] = self.partner_ref
        return result
