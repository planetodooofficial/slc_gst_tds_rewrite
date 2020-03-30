from odoo import api, fields, models, _


class AccountTaxTDS(models.Model):
    _inherit = "account.tax"

    apply_tds = fields.Boolean('Apply TDS', default=False)


class AccountMove(models.Model):
    _inherit = "account.move"

    # TDS
    apply_tds = fields.Boolean(string='Apply TDS', default=False, readonly=True,
                               states={'draft': [('readonly', False)]})
    tds_ids = fields.Many2one('account.tax', string='TDS',
                              states={'draft': [('readonly', False)]})
    tds_added = fields.Monetary(string='TDS Amount added',
                                store=True, readonly=True, compute='_compute_amount')
    total_tds = fields.Monetary(string='Total Amount',
                                store=True, readonly=True, compute='_compute_amount')
    total_tds_amount = fields.Monetary(string='Total Amount After TDS',
                                       store=True, readonly=True, compute='_compute_amount')
    vendor_type = fields.Selection(related='partner_id.company_type', string='Select Partner')

    def turnover_compute(self, partner_id, limit, total_tds):
        account_move = self.env['account.move.line'].search(
            [
                ('partner_id', '=', partner_id),
                ('account_id.internal_type', '=', 'payable'),
                ('account_id.reconcile', '=', True),
                ('move_id.state', '=', 'posted')
            ])
        account_credit = sum([account.credit for account in account_move])
        account_credit = account_credit + total_tds
        if account_credit < limit:
            return False
        else:
            return True

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.currency_id', 'line_ids.amount_currency',
                 'line_ids.amount_residual', 'line_ids.amount_residual_currency', 'line_ids.payment_id.state',
                 'tds_ids')
    def _compute_amount(self):
        super(AccountMove, self)._compute_amount()
        for account_move in self:
            account_move.tds_added = -(account_move.tds_ids.amount * (account_move.total_tds / 100))
            account_move.total_tds = account_move.amount_untaxed + account_move.amount_tax
            account_move.total_tds_amount = account_move.amount_untaxed + account_move.amount_tax + account_move.tds_added
            tds_applicable = True
            if account_move.partner_id and account_move.partner_id.check_threshold and account_move.tds_ids:
                tds_applicable = account_move.turnover_compute(account_move.partner_id.id,
                                                               account_move.tds_ids.excess_of,
                                                               account_move.total_tds)
            if not tds_applicable:
                account_move.tds_added = 0

    @api.onchange('tds_ids', 'apply_tds')
    def tds_ids_onchange(self):
        tds_applicable = True
        for tds in self:

            if tds.partner_id and tds.partner_id.check_threshold:
                tds_applicable = tds.turnover_compute(tds.partner_id.id, tds.tds_ids.excess_of,
                                                      tds.total_tds)

            if tds.currency_id != tds.company_id.currency_id:
                tds_currency_id = tds.currency_id.id
            else:
                tds_currency_id = False

            if tds.tds_ids:
                tds_tax_lines = tds.tds_ids.invoice_repartition_line_ids.filtered(
                    lambda t: t.repartition_type == 'tax')
            else:
                tds_tax_lines = None

            if tds_tax_lines:
                tax_lines = tds.line_ids.filtered(
                    lambda t: t.account_id.id == tds_tax_lines.account_id.id)
            else:
                tax_lines = None

            if tds.apply_tds and tds_applicable:
                tds_amount = abs(tds.tds_added)
            else:
                tds_amount = 0
            if tds.tds_ids:
                tds_tax = tds.tds_ids
            else:
                tds_tax = None
            account_credit = 0
            account_debit = 0
            if tds.type in ['in_invoice']:
                account_credit = tds_amount
            elif tds.type in ['out_invoice']:
                account_debit = tds_amount
            if tds_amount and tds_tax and tds_applicable and tds_tax and tds_tax_lines:
                if tax_lines:
                    tax_lines.credit = account_credit
                    tax_lines.debit = account_debit
                else:
                    create_method = tds.env['account.move.line'].new
                    create_method({
                        'name': tds_tax.name,
                        'debit': account_debit,
                        'credit': account_credit,
                        'quantity': 1.0,
                        'amount_currency': tds_amount,
                        'date_maturity': tds.invoice_date,
                        'move_id': tds.id,
                        'currency_id': tds_currency_id,
                        'account_id': tds_tax_lines.id and tds_tax_lines.account_id.id,
                        'partner_id': tds.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                tds._onchange_recompute_dynamic_lines()
            elif tax_lines:
                tax_lines.credit = 0
                tds._onchange_recompute_dynamic_lines()
                tds.line_ids -= tax_lines

    # GST
    invoice_type_status = fields.Selection([
        ('yet_to_upload', 'Yet to Upload'),
        ('ready_upload', 'Ready to upload'),
        ('upload_complete', 'Upload Complete'),
        ('filed', 'Filed Documents')
    ],
        string='Invoice Status',
        default="yet_to_upload",
        copy=False
    )
    invoice_type = fields.Selection([('import', 'Import'),
                                     ('export', 'Export'),
                                     ('b2b', 'B2B'),
                                     ('b2bur', 'B2BUR'),
                                     ('b2cl', 'B2CL'),
                                     ('b2cs', 'B2CS')],
                                    copy=False,
                                    string='Invoice Type')
    export = fields.Selection([('with_pay', 'WPay'), ('without_pay', 'WoPay')], string='Export')
    avail_itc_eligible = fields.Selection([
        ('Inputs', 'Inputs'),
        ('Capital goods', 'Capital goods'),
        ('Input services', 'Input services'),
        ('Ineligible', 'Ineligible'),
    ],
        string='Eligibility to avail ITC',
        default='Ineligible'
    )
    reverse_charge = fields.Boolean(string='Reverse Charge')
    amount_total = fields.Float(string='Total Amount(INR)')
