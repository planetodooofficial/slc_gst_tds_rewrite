# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    origin = fields.Char(string='Source Document', help="Reference of the document that generated this from purchase order request.")
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order')
    amount_untaxed = fields.Float('Untaxed Amount')
    amount_tax = fields.Float('Taxes')
    amount_to_pay = fields.Float('Amount to Pay',required=True)

    @api.model
    def default_get(self, fields):
        """
            To pass amount_untaxed and amount_tax value to payment record
            if that payment record is advance payment(payment generating from purchase order)
        """
        result = super(AccountPayment, self).default_get(fields)
        active_model = self._context.get('active_model')
        if active_model == 'purchase.order':
            active_id = self._context.get('active_id')
            purchase_id = self.env['purchase.order'].browse(active_id)
            result['amount_untaxed'] = purchase_id.amount_untaxed
            result['amount_tax'] = purchase_id.amount_tax
            result['amount'] = purchase_id.amount_total
            result['amount_to_pay'] = purchase_id.amount_total
        return result

    @api.model
    def create(self, vals):
        """To pass amount_to_pay value"""
        res = super(AccountPayment, self).create(vals)
        # if res.purchase_id:
        res.update({'amount': res.amount_to_pay})
        return res

    def write(self, vals):
        """To pass amount_to_pay value"""
        if self.purchase_id:
            if vals.get('amount_to_pay'):
                vals.update({'amount': vals.get('amount_to_pay')})
        res = super(AccountPayment, self).write(vals)
        return res

    @api.onchange('tds', 'tds_tax_id', 'amount', 'amount_untaxed', 'amount_tax', 'amount_to_pay')
    @api.depends('tds', 'tds_tax_id', 'amount', 'amount_untaxed', 'amount_tax', 'amount_to_pay')
    def onchange_tds(self):
        """Override : To pass amount_untaxed value instead of amount"""
        for payment in self:
            if payment.tds and payment.tds_tax_id:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    if payment.purchase_id:
                        applicable = self.check_turnover(self.partner_id.id, self.tds_tax_id.payment_excess, self.amount_to_pay)
                    else:
                        applicable = self.check_turnover(self.partner_id.id, self.tds_tax_id.payment_excess, self.amount)
                if applicable:
                    if payment.purchase_id:
                        payment.tds_amt = (payment.tds_tax_id.amount * payment.amount_untaxed / 100)
                        payment.amount_to_pay = payment.amount_untaxed + payment.amount_tax - payment.tds_amt
                        payment.amount = payment.amount_untaxed + payment.amount_tax - payment.tds_amt
                    else:
                        payment.tds_amt = (payment.tds_tax_id.amount * payment.amount / 100)
                else:
                    payment.tds_amt = 0.0









