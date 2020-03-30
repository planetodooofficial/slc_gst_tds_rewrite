# -*- coding: utf-8 -*-
import json
from datetime import timedelta
from babel.dates import format_datetime, format_date

from odoo import models, api, _, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class DashboardGST(models.Model):
    _name = "gst.dashboard"
    name = fields.Char(string="Name")
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    invoice_type = fields.Selection([('import', 'Import'),
                                     ('export', 'Export'),
                                     ('b2b', 'B2B'),
                                     ('b2bur', 'B2BUR'),
                                     ('b2cl', 'B2CL'),
                                     ('b2cs', 'B2CS')])
    count_yet_to_upload = fields.Integer(string='Count for Yet to Upload', compute='_get_count')
    count_ready_upload = fields.Integer(string='Count for Ready to Upload', compute='_get_count')
    count_upload_complete = fields.Integer(string='Count for Upload Complete', compute='_get_count')
    count_filed = fields.Integer(string='Count for Filed Documents', compute='_get_count')
    color = fields.Integer(string='Color')
    amount_yet_to_upload = fields.Integer(string='Not Uploaded Amount', compute='_get_amount')
    amount_ready_upload = fields.Integer(string='Ready to Upload Amount', compute='_get_amount')
    amount_upload_complete = fields.Integer(string='Uploaded Amount', compute='_get_amount')
    amount_filed = fields.Integer(string='Filed Amount', compute='_get_amount')

    def _kanban_dashboard_graph(self):
        for rec in self:
            rec.kanban_dashboard_graph = json.dumps(rec.get_bar_graph_datas(rec.invoice_type))

    def _get_amount(self):
        for amount in self:
            amount.amount_yet_to_upload = amount.compute_total_amount('yet_to_upload')
            amount.amount_ready_upload = amount.compute_total_amount('ready_upload')
            amount.amount_upload_complete = amount.compute_total_amount('upload_complete')
            amount.amount_filed = amount.compute_total_amount('filed')

    def compute_total_amount(self, invoice_type_status):
        amount_total = 0
        account_move = self.env['account.move'].search([
            ('invoice_type', '=', self.invoice_type),
            ('invoice_type_status', '=', invoice_type_status)
        ])
        for moves in account_move:
            amount_total += moves.amount_total
        return amount_total

    def invoice_type_action(self):
        self.ensure_one()
        invoice_type = self.invoice_type
        vals = [('invoice_type', '=', invoice_type)]
        res = self.get_action_records(vals)
        return res

    def get_attachments(self):
        self.ensure_one()
        name = "{}_".format(self.invoice_type)
        if self.invoice_type == 'import':
            name = "imp_"
        attachment = self.env['ir.attachment'].search([('name', 'like', name),
                                                       ('res_model', '=', 'gst.return.tool')])
        attachment = attachment.ids
        return {
            'name': 'GST Attachments',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'ir.attachment',
            'view_id': False,
            'domain': [('id', 'in', attachment)],
            'target': 'current',
        }

    def _get_count(self):
        for count in self:
            count_yet_to_upload = len(self.env['account.move'].search([
                ('invoice_type', '=', count.invoice_type),
                ('invoice_type_status', '=', 'yet_to_upload')
            ]))
            count_ready_upload = len(self.env['account.move'].search([
                ('invoice_type', '=', count.invoice_type),
                ('invoice_type_status', '=', 'ready_upload')
            ]))
            count_upload_complete = len(self.env['account.move'].search([
                ('invoice_type', '=', count.invoice_type),
                ('invoice_type_status', '=', 'upload_complete')
            ]))
            count_filed = len(self.env['account.move'].search([
                ('invoice_type', '=', count.invoice_type),
                ('invoice_type_status', '=', 'filed')
            ]))
            count.count_yet_to_upload = count_yet_to_upload
            count.count_ready_upload = count_ready_upload
            count.count_upload_complete = count_upload_complete
            count.count_filed = count_filed

    def get_gst_invoice(self):
        self.ensure_one()
        context = self._context.copy()
        name = "{}_".format(self.invoice_type)
        attachment_obj = self.env['ir.attachment'].search([('name', 'ilike', name),
                                                           ('res_model', '=', 'gst.return.tool')])
        attachment = []
        for rec in attachment_obj:
            attachment.append(rec.res_id)
        if context.get('status'):
            attachment = self.env['gst.return.tool'].search([
                ('status', '=', context.get('status')), ('id', 'in', attachment)]).ids
        return {
            'name': 'GST Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'gst.return.tool',
            'domain': [('id', 'in', attachment)],
            'target': 'current',
        }

    def action_create_new(self):
        if self._context.copy().get('obj') == 'Invoice':
            self._context.copy().update({
                'default_type': 'out_invoice',
                'type': 'out_invoice',
                'invoice_type': self.invoice_type
            })
            return {
                'name': _("Create Invoice"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'view_id': self.env.ref('account.view_move_form').id,
                'context': self._context.copy(),
            }
        else:
            return {
                'name': _("GST Invoice"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'gst.return.tool',
                'view_id': self.env.ref('slc_gst_tds_rewrite.gstr1_tool_form').id,
                'context': self._context.copy(),
            }

    def action_invoice_status(self):
        self.ensure_one()
        vals = [('invoice_type', '=', self.invoice_type)]
        if self._context.copy().get('invoice_type_status'):
            vals.append(('invoice_type_status', '=', self._context.copy().get('invoice_type_status')))
        return self.get_action_records(vals)

    def get_bar_graph_datas(self, invoice_type):
        self.ensure_one()
        graph_data = [{'label': _('Past'), 'value': 0.0}]
        day = int(format_datetime(fields.Date.context_today(self),
                                  'e', locale=self._context.get('lang', 'en_US')))
        for i in range(-1, 2):
            if i < 0:
                time_type = 'past'
            else:
                time_type = 'future'
            if i == 0:
                label = _('This Week')
            elif i == 1:
                label = _('Future')
            else:
                first = fields.Date.context_today(self) + timedelta(days=-day + 1) + timedelta(days=i * 7)
                last = first + timedelta(days=6)
                if first.month == last.month:
                    label = str(first.day) + '-' + str(last.day) + ' ' + \
                            format_date(last, 'MMM', locale=self._context.get('lang', 'en_US'))
                else:
                    label = format_date(first, 'd MMM', locale=self._context.get('lang', 'en_US')) + '-' + \
                            format_date(last, 'd MMM', locale=self._context.get('lang', 'en_US'))
            graph_data.append({
                'label': label,
                'value': 0.0,
                'type': time_type
            })
        res = 'account_move'
        select_account_move = """SELECT COUNT(*) as total FROM """ + res + """ where invoice_type = %(invoice_type)s """
        account_move_query = ''
        first_day = (fields.Date.context_today(self) + timedelta(days=-day + 1) + timedelta(days=-7))
        for i in range(0, 4):
            if i == 0:
                account_move_query += "(" + select_account_move + " and " + 'invoice_date' + " < '" + \
                                      first_day.strftime(DF) + "')"
            elif i == 3:
                account_move_query += " UNION ALL (" + select_account_move + " and date >= '" + \
                                      first_day.strftime(DF) + "')"
            else:
                next_day = first_day + timedelta(days=7)
                account_move_query += " UNION ALL (" + select_account_move + " and " + 'invoice_date' + " >= '" + \
                                      first_day.strftime(DF) + "' and " + 'invoice_date' + " < '" + \
                                      next_day.strftime(DF) + "')"
                first_day = next_day

        self.env.cr.execute(account_move_query, {'invoice_type': self.invoice_type})
        final_query = self.env.cr.dictfetchall()
        for i in range(0, len(final_query)):
            graph_value = str(final_query[i].get('total'))
            graph_value = graph_value.split('L')
            if int(graph_value[0]) > 0:
                graph_data[i]['value'] = graph_value[0]

        return [{
            'values': graph_data,
            'area': True,
            'key': invoice_type.upper(),
            'color': '#6e4287'
        }]

    def get_action_records(self, vals=[]):
        self.ensure_one()
        return {
            'name': 'Records',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree, form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': [('id', 'in', self.env['account.move'].search(vals).ids)],
            'target': 'current',
        }

