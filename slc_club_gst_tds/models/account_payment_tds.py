# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class account_payment(models.Model):
    _inherit = "account.payment"

    tds = fields.Boolean('TDS / Withholding', default=False)
    tds_tax_id = fields.Many2one('account.tax', string='TDS')
    tds_amt = fields.Float('TDS Amount')
    vendor_type = fields.Selection(related='partner_id.company_type', string='Partner Type')

    @api.onchange('tds', 'tds_tax_id', 'amount')
    @api.depends('tds', 'tds_tax_id', 'amount')
    def onchange_tds(self):
        for payment in self:
            if payment.tds and payment.tds_tax_id and payment.amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = self.check_turnover(self.partner_id.id, self.tds_tax_id.payment_excess, self.amount)
                if applicable:
                    payment.tds_amt = (payment.tds_tax_id.amount * payment.amount / 100)
                else:
                    payment.tds_amt = 0.0

    def check_turnover(self, partner_id, threshold, amount):
        if self.payment_type == 'outbound':
            domain = [('partner_id', '=', partner_id), ('account_id.internal_type', '=', 'payable'),
                      ('move_id.state', '=', 'posted'), ('account_id.reconcile', '=', True)]
            journal_items = self.env['account.move.line'].search(domain)
            credits = sum([item.credit for item in journal_items])
            credits += amount
            if credits >= threshold:
                return True
            else:
                return False
        elif self.payment_type == 'inbound':
            domain = [('partner_id', '=', partner_id), ('account_id.internal_type', '=', 'receivable'),
                      ('move_id.state', '=', 'posted'), ('account_id.reconcile', '=', True)]
            journal_items = self.env['account.move.line'].search(domain)
            debits = sum([item.debit for item in journal_items])
            debits += amount
            if debits >= threshold:
                return True
            else:
                return False

    def _prepare_payment_moves(self):
        all_move_vals = super(account_payment, self)._prepare_payment_moves()
        applicable = True
        for payment in self:
            if payment.partner_id and payment.partner_id.tds_threshold_check:
                applicable = payment.check_turnover(payment.partner_id.id, payment.tds_tax_id.payment_excess,
                                                    payment.amount)
            if payment.currency_id == payment.company_id.currency_id:
                # Single-currency.
                currency_id = False
            else:
                # Multi-currencies.
                currency_id = payment.currency_id.id
            if payment.tds and payment.tds_tax_id and payment.tds_amt and applicable:
                tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax')
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    for rec in all_move_vals[0].get('line_ids'):
                        if rec[2]['debit']:
                            rec[2]['debit'] = rec[2]['debit'] - payment.tds_amt
                    all_move_vals[0]['line_ids'].append((0, 0, {
                        'name': _('Counterpart'),
                        'amount_currency': payment.tds_amt,
                        'currency_id': currency_id,
                        'debit': payment.tds_amt,
                        'credit': 0,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.id,
                        'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                        'payment_id': payment.id,
                    }))
                elif payment.payment_type == 'inbound' and payment.partner_type == 'customer':
                    for rec in all_move_vals[0].get('line_ids'):
                        if rec[2]['credit']:
                            rec[2]['credit'] = rec[2]['credit'] - payment.tds_amt
                        print('...rec[2][', rec[2]['credit'], payment.tds_amt)
                    all_move_vals[0]['line_ids'].append((0, 0, {
                        'name': _('Counterpart'),
                        'amount_currency': payment.tds_amt,
                        'currency_id': currency_id,
                        'debit': 0,
                        'credit': payment.tds_amt,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.id,
                        'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                        'payment_id': payment.id,
                    }))
            return all_move_vals

    def _create_payment_entry(self, amount):
        applicable = True
        if self.partner_id and self.partner_id.tds_threshold_check:
            applicable = self.check_turnover(self.partner_id.id, self.tds_tax_id.payment_excess, amount)
        if self.tds and self.tds_tax_id and self.tds_amt and applicable:
            aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
            invoice_currency = False
            if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
                # if all the invoices selected share the same currency, record the payment in that currency too
                invoice_currency = self.invoice_ids[0].currency_id
            debit, credit, amount_currency, currency_id = aml_obj.with_context(
                date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)
            move = self.env['account.move'].create(self._get_move_vals())

            # Write line corresponding to invoice payment
            counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
            counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            counterpart_aml_dict.update({'currency_id': currency_id})
            counterpart_aml = aml_obj.create(counterpart_aml_dict)

            # Reconcile with the invoices
            payment_difference_handling = 'reconcile'
            payment_difference = self.tds_amt
            writeoff_account_id = self.tds_tax_id and self.tds_tax_id.account_id

            if payment_difference_handling == 'reconcile' and payment_difference:
                writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
                debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(
                    date=self.payment_date)._compute_amount_fields(payment_difference, self.currency_id,
                                                                   self.company_id.currency_id)
                writeoff_line['name'] = _('Counterpart')
                writeoff_line['account_id'] = writeoff_account_id.id
                writeoff_line['debit'] = debit_wo
                writeoff_line['credit'] = credit_wo
                writeoff_line['amount_currency'] = amount_currency_wo
                writeoff_line['currency_id'] = currency_id
                writeoff_line = aml_obj.create(writeoff_line)
                if counterpart_aml['debit']:
                    counterpart_aml['debit'] += credit_wo - debit_wo
                if counterpart_aml['credit']:
                    counterpart_aml['credit'] += debit_wo - credit_wo
                counterpart_aml['amount_currency'] -= amount_currency_wo
            self.invoice_ids.register_payment(counterpart_aml)

            # Write counterpart lines
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
            aml_obj.create(liquidity_aml_dict)

            move.post()
            return move
        return super(account_payment, self)._create_payment_entry(amount)