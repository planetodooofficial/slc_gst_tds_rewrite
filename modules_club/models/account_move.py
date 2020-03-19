# -*- coding: utf-8 -*-
import json
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    gst_status = fields.Selection([
        ('not_uploaded', 'Not Uploaded'),
        ('ready_to_upload', 'Ready to upload'),
        ('uploaded', 'Uploaded to govt'),
        ('filed', 'Filed')
    ],
        string='GST Status',
        default="not_uploaded",
        copy=False,
        help="status will be consider during gst import, "
    )
    invoice_type = fields.Selection([
        ('b2b', 'B2B'),
        ('b2cl', 'B2CL'),
        ('b2cs', 'B2CS'),
        ('b2bur', 'B2BUR'),
        ('import', 'IMPS/IMPG'),
        ('export', 'Export')
    ],
        copy=False,
        string='Invoice Type')
    export = fields.Selection([
        ('WPAY', 'WPay'),
        ('WOPAY', 'WoPay')
    ],
        string='Export'
    )
    itc_eligibility = fields.Selection([
        ('Inputs', 'Inputs'),
        ('Capital goods', 'Capital goods'),
        ('Input services', 'Input services'),
        ('Ineligible', 'Ineligible'),
    ],
        string='ITC Eligibility',
        default='Ineligible'
    )
    reverse_charge = fields.Boolean(
        string='Reverse Charge',
        help="Allow reverse charges for b2b invoices")
    inr_total = fields.Float(string='INR Total')

    filter_adv_payment = fields.Boolean('Filter outstanding debits against this PO')

    tds = fields.Boolean('Apply TDS', default=False, readonly=True,
                         states={'draft': [('readonly', False)]})
    tds_tax_id = fields.Many2one('account.tax', string='TDS',
                                 states={'draft': [('readonly', False)]})
    tds_amt = fields.Monetary(string='TDS Amount',
                              store=True, readonly=True, compute='_compute_amount')
    total_gross = fields.Monetary(string='Total',
                                  store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Monetary(string='Net Total',
                                   store=True, readonly=True, compute='_compute_amount')
    vendor_type = fields.Selection(related='partner_id.company_type', string='Partner Type')

    def _compute_payments_widget_to_reconcile_info(self):
        """
            Override : To filter payment records which is related to particular PO
        """
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' or move.invoice_payment_state != 'not_paid' or not move.is_invoice(
                    include_receipts=True):
                continue
            pay_term_line_ids = move.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [('account_id', 'in', pay_term_line_ids.mapped('account_id').ids),
                      '|', ('move_id.state', '=', 'posted'), '&', ('move_id.state', '=', 'draft'),
                      ('journal_id.post_at', '=', 'bank_rec'),
                      ('partner_id', '=', move.commercial_partner_id.id),
                      ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)]

            if move.is_inbound():
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'move_id': move.id}
            lines = self.env['account.move.line'].search(domain)

            # filter to take only PO related payments
            if move.filter_adv_payment:
                purchase_id = move.mapped('invoice_line_ids.purchase_line_id.order_id')
                if purchase_id:
                    lines = lines.filtered(lambda line: line.payment_id != False)
                    if lines:
                        lines = lines.filtered(lambda line: line.payment_id.purchase_id.id == purchase_id.id)

            currency_id = move.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == move.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), move.currency_id, move.company_id,
                                                           line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=move.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, move.currency_id.decimal_places],
                        'payment_date': fields.Date.to_string(line.date),
                    })
                info['title'] = type_payment
                move.invoice_outstanding_credits_debits_widget = json.dumps(info)
                move.invoice_has_outstanding = True

        @api.depends(
            'line_ids.debit',
            'line_ids.credit',
            'line_ids.currency_id',
            'line_ids.amount_currency',
            'line_ids.amount_residual',
            'line_ids.amount_residual_currency',
            'line_ids.payment_id.state', 'tds_tax_id')
        def _compute_amount(self):
            super(AccountMove, self)._compute_amount()
            for move in self:
                move.tds_amt = -(move.tds_tax_id.amount * (move.total_gross / 100))
                move.total_gross = move.amount_untaxed + move.amount_tax
                move.amount_total = move.amount_untaxed + move.amount_tax + move.tds_amt
                applicable = True
                if move.partner_id and move.partner_id.tds_threshold_check and move.tds_tax_id:
                    applicable = move.check_turnover(move.partner_id.id, move.tds_tax_id.payment_excess,
                                                     move.total_gross)
                if not applicable:
                    move.tds_amt = 0

        def check_turnover(self, partner_id, threshold, total_gross):
            domain = [('partner_id', '=', partner_id), ('account_id.internal_type', '=', 'payable'),
                      ('move_id.state', '=', 'posted'), ('account_id.reconcile', '=', True)]
            journal_items = self.env['account.move.line'].search(domain)
            credits = sum([item.credit for item in journal_items])
            credits += total_gross
            if credits >= threshold:
                return True
            else:
                return False

        @api.onchange('tds_tax_id', 'tds')
        def _onchange_tds_tax_id(self):
            for invoice in self:
                applicable = True
                if invoice.partner_id and invoice.partner_id.tds_threshold_check:
                    applicable = invoice.check_turnover(invoice.partner_id.id, invoice.tds_tax_id.payment_excess,
                                                        invoice.total_gross)
                tax_repartition_lines = invoice.tds_tax_id.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax') if invoice.tds_tax_id else None
                existing_line = invoice.line_ids.filtered(
                    lambda x: x.account_id.id == tax_repartition_lines.account_id.id) if tax_repartition_lines else None
                tds_amount = abs(invoice.tds_amt) if invoice.tds and applicable else 0
                tds_tax = invoice.tds_tax_id if invoice.tds_tax_id else None
                credit = 0
                debit = 0
                if invoice.type in ['in_invoice']:
                    credit = tds_amount
                elif invoice.type in ['out_invoice']:
                    debit = tds_amount
                if applicable and tds_amount and tds_tax and tax_repartition_lines:
                    if existing_line:
                        existing_line.credit = credit
                        existing_line.debit = debit
                    else:
                        create_method = invoice.env['account.move.line'].new
                        create_method({
                            'name': tds_tax.name,
                            'debit': debit,
                            'credit': credit,
                            'quantity': 1.0,
                            'amount_currency': tds_amount,
                            'date_maturity': invoice.invoice_date,
                            'move_id': invoice.id,
                            'currency_id': invoice.currency_id.id if invoice.currency_id != invoice.company_id.currency_id else False,
                            'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                            'partner_id': invoice.commercial_partner_id.id,
                            'exclude_from_invoice_tab': True,
                        })
                    invoice._onchange_recompute_dynamic_lines()
                elif existing_line:
                    existing_line.credit = 0
                    invoice._onchange_recompute_dynamic_lines()
                    invoice.line_ids -= existing_line


class AccountInvoiceTax(models.Model):
    _inherit = "account.tax"

    tds = fields.Boolean('TDS', default=False)
