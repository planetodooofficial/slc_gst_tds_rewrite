from odoo import api, fields, models, _


class PaymentAccountTDS(models.Model):
    _inherit = "account.payment"

    apply_tds = fields.Boolean('Apply TDS', default=False)
    tds_ids = fields.Many2one('account.tax', string='Select TDS')
    tds_added = fields.Float('TDS amount added')
    partner_type = fields.Selection(related='partner_id.company_type', string='Select Partner')

    def turnover_compute(self, partner_id, limit, amount):
        if self.payment_type == 'outbound':
            account_move = self.env['account.move.line'].search(
                [('partner_id', '=', partner_id),
                 ('account_id.internal_type', '=', 'payable'),
                 ('move_id.state', '=', 'posted'),
                 ('account_id.reconcile', '=', True)])
            account_credit = sum([account.credit for account in account_move])
            account_credit += amount
            if account_credit <= limit:
                return False
            else:
                return True
        elif self.payment_type == 'inbound':
            account_move = self.env['account.move.line'].search(
                [('partner_id', '=', partner_id),
                 ('account_id.internal_type', '=', 'receivable'),
                 ('move_id.state', '=', 'posted'),
                 ('account_id.reconcile', '=', True)])
            account_debit = sum([account.debit for account in account_move])
            account_debit += amount
            if account_debit <= limit:
                return False
            else:
                return True

    def _prepare_payment_moves(self):
        prepare_payment_moves = super(PaymentAccountTDS, self)._prepare_payment_moves()
        tds_applicable = True
        for tds in self:
            if tds.partner_id and tds.partner_id.check_threshold:
                tds_applicable = tds.turnover_compute(tds.partner_id.id, tds.tds_ids.excess_of,
                                                      tds.amount)
            if tds.currency_id == tds.company_id.currency_id:
                tds_currency_id = False
            else:
                tds_currency_id = tds.currency_id.id
            if tds.apply_tds and tds.tds_ids and tds.tds_added and tds_applicable:
                tds_tax_lines = tds.tds_ids.invoice_repartition_line_ids.filtered(
                    lambda t: t.repartition_type == 'tax')
                if tds.payment_type == 'outbound' and tds.partner_type == 'supplier':
                    for rec in prepare_payment_moves[0].get('line_ids'):
                        if rec[2]['debit']:
                            rec[2]['debit'] = rec[2]['debit'] - tds.tds_added
                    prepare_payment_moves[0]['line_ids'].append((0, 0, {
                        'name': _('Counterpart'),
                        'amount_currency': tds.tds_added,
                        'debit': tds.tds_added,
                        'credit': 0,
                        'date_maturity': tds.payment_date,
                        'partner_id': tds.partner_id.id,
                        'account_id': tds_tax_lines.id and tds_tax_lines.account_id.id,
                        'payment_id': tds.id,
                        'currency_id': tds_currency_id,

                    }))
                elif tds.payment_type == 'inbound' and tds.partner_type == 'customer':
                    for rec in prepare_payment_moves[0].get('line_ids'):

                        if rec[2]['credit']:
                            rec[2]['credit'] = rec[2]['credit'] - tds.tds_added
                        print('...rec[2][', rec[2]['credit'], tds.tds_added)
                    prepare_payment_moves[0]['line_ids'].append((0, 0, {
                        'name': _('Counterpart'),
                        'amount_currency': tds.tds_added,
                        'currency_id': tds_currency_id,
                        'debit': 0,
                        'credit': tds.tds_added,
                        'date_maturity': tds.payment_date,
                        'partner_id': tds.partner_id.id,
                        'account_id': tds_tax_lines.id and tds_tax_lines.account_id.id,
                        'payment_id': tds.id,
                    }))
            return prepare_payment_moves

    @api.onchange('apply_tds', 'tds_ids', 'amount')
    @api.depends('apply_tds', 'tds_ids', 'amount')
    def apply_tds_onchange(self):
        for tds in self:
            if tds.apply_tds and tds.tds_ids and tds.amount:
                tds_applicable = True
                if tds.partner_id and tds.partner_id.check_threshold:
                    tds_applicable = self.turnover_compute(self.partner_id.id, self.tds_ids.excess_of, self.amount)
                if tds_applicable:
                    tds.tds_added = (tds.tds_ids.amount * tds.amount / 100)
                else:
                    tds.tds_added = 0.0

    def _create_payment_entry(self, amount):
        tds_applicable = True
        if self.partner_id and self.partner_id.check_threshold:
            tds_applicable = self.turnover_compute(self.partner_id.id, self.tds_ids.excess_of, amount)
        if self.apply_tds and self.tds_ids and self.tds_added and tds_applicable:
            account_move_obj = self.env['account.move.line'].with_context(check_move_validity=False)
            tds_currency_id = False
            if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
                tds_currency_id = self.invoice_ids[0].currency_id
            debit, credit, amount_currency, currency_id = account_move_obj.with_context(
                date=self.payment_date)._compute_amount_fields \
                (amount, self.currency_id,
                 self.company_id.currency_id)
            account_move = self.env['account.move'].create(self._get_move_vals())

            invoice_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, account_move.id, False)
            invoice_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            invoice_dict.update({'currency_id': currency_id})
            counterpart_aml = account_move_obj.create(invoice_dict)

            # Reconcile with the invoices
            payment_difference_handling = 'reconcile'
            payment_difference = self.tds_added
            writeoff_account_id = self.tds_ids and self.tds_ids.account_id

            if payment_difference_handling == 'reconcile' and payment_difference:
                writeoff_line = self._get_shared_move_line_vals(0, 0, 0, account_move.id, False)
                debit_wo, credit_wo, amount_currency_wo, currency_id = account_move_obj.with_context(
                    date=self.payment_date)._compute_amount_fields(payment_difference, self.currency_id,
                                                                   self.company_id.currency_id)
                writeoff_line['name'] = _('Counterpart')
                writeoff_line['account_id'] = writeoff_account_id.id
                writeoff_line['debit'] = debit_wo
                writeoff_line['credit'] = credit_wo
                writeoff_line['amount_currency'] = amount_currency_wo
                writeoff_line['currency_id'] = currency_id
                writeoff_line = account_move_obj.create(writeoff_line)
                if counterpart_aml['debit']:
                    counterpart_aml['debit'] += credit_wo - debit_wo
                if counterpart_aml['credit']:
                    counterpart_aml['credit'] += debit_wo - credit_wo
                counterpart_aml['amount_currency'] -= amount_currency_wo
            self.invoice_ids.register_payment(counterpart_aml)

            # Write counterpart lines
            if not self.currency_id != self.company_id.currency_id:
                tds_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -tds_currency, account_move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
            account_move_obj.create(liquidity_aml_dict)

            account_move.post()
            return account_move
        return super(PaymentAccountTDS, self)._create_payment_entry(amount)
