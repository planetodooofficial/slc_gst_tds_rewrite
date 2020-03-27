# -*- coding: utf-8 -*-
import json
from datetime import timedelta
from babel.dates import format_datetime, format_date

from odoo import models, api, _, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class gst_dashboard(models.Model):
    _name = "gst.dashboard"
    name = fields.Char(string="Name")
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    invoice_type = fields.Selection([('import', 'Import'),
                                     ('export', 'Export'),
                                     ('b2b', 'B2B'),
                                     ('b2bur', 'B2BUR'),
                                     ('b2cl', 'B2CL'),
                                     ('b2cs', 'B2CS')])
    color = fields.Integer(string='Color Index')
    count_yet_to_upload = fields.Integer(string='Count for Yet to Upload', compute='_get_count')
    count_ready_upload = fields.Integer(string='Count for Ready to Upload', compute='_get_count')
    count_upload_complete = fields.Integer(string='Count for Upload Complete', compute='_get_count')
    count_filed = fields.Integer(string='Count for Filed Documents', compute='_get_count')
    amount_yet_to_upload = fields.Integer(string='Not Uploaded Amount', compute='_get_amount')
    amount_ready_upload = fields.Integer(string='Ready to Upload Amount', compute='_get_amount')
    amount_upload_complete = fields.Integer(string='Uploaded Amount', compute='_get_amount')
    amount_filed = fields.Integer(string='Filed Amount', compute='_get_amount')

    def _kanban_dashboard_graph(self):
        for rec in self:
            rec.kanban_dashboard_graph = json.dumps(rec.get_bar_graph_datas(rec.invoice_type))

    def _get_amount(self):
        for rec in self:
            rec.amount_yet_to_upload = rec.compute_total_amount('not_uploaded')
            rec.amount_ready_upload = rec.compute_total_amount('ready_to_upload')
            rec.amount_upload_complete = rec.compute_total_amount('uploaded')
            rec.amount_filed = rec.compute_total_amount('filed')

    def compute_total_amount(self, gst_status):
        amount_total = 0
        account_move = self.env['account.move'].search([
            ('invoice_type', '=', self.invoice_type),
            ('gst_status', '=', gst_status)
        ])
        for moves in account_move:
            amount_total += moves.inr_total
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
                                                       ('res_model', '=', 'gstr1.tool')])
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
        for rec in self:
            count_yet_to_upload = len(self.env['account.move'].search([
                ('invoice_type', '=', rec.invoice_type),
                ('gst_status', '=', 'not_uploaded')
            ]))
            count_ready_upload = len(self.env['account.move'].search([
                ('invoice_type', '=', rec.invoice_type),
                ('gst_status', '=', 'ready_to_upload')
            ]))
            count_upload_complete = len(self.env['account.move'].search([
                ('invoice_type', '=', rec.invoice_type),
                ('gst_status', '=', 'uploaded')
            ]))
            count_filed = len(self.env['account.move'].search([
                ('invoice_type', '=', rec.invoice_type),
                ('gst_status', '=', 'filed')
            ]))
            rec.count_yet_to_upload = count_yet_to_upload
            rec.count_ready_upload = count_ready_upload
            rec.count_upload_complete = count_upload_complete
            rec.count_filed = count_filed

    def get_gst_invoice(self):
        self.ensure_one()
        context = self._context.copy()
        name = "{}_".format(self.invoice_type)
        attachment_obj = self.env['ir.attachment'].search([('name', 'ilike', name),
                                                           ('res_model', '=', 'gstr1.tool')])
        attachment = []
        for rec in attachment_obj:
            attachment.append(rec.res_id)
        if context.get('status'):
            attachment = self.env['gstr1.tool'].search([
                ('status', '=', context.get('status')), ('id', 'in', attachment)]).ids
        return {
            'name': 'GST Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'gstr1.tool',
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
                'res_model': 'gstr1.tool',
                'view_id': self.env.ref('slc_gst_tds_rewrite.gstr1_tool_form').id,
                'context': self._context.copy(),
            }

    def action_invoice_status(self):
        self.ensure_one()
        vals = [('invoice_type', '=', self.invoice_type)]
        if self._context.copy().get('gst_status'):
            vals.append(('gst_status', '=', self._context.copy().get('gst_status')))
        return self.get_action_records(vals)

    def get_action_records(self, vals=[]):
        self.ensure_one()
        return {
            'name':'Records',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree, form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': [('id', 'in', self.env['account.move'].search(vals).ids)],
            'target': 'current',
        }

    def get_bar_graph_datas(self, invoice_type):
        self.ensure_one()
        res_model = 'account_move'
        fecthDate = 'invoice_date'
        data = []
        today = fields.Date.context_today(self)
        locale = self._context.get('lang', 'en_US')
        data.append({'label': _('Past'), 'value': 0.0})
        day_of_week = int(format_datetime(today, 'e', locale=locale))
        first_day_of_week = today + timedelta(days=-day_of_week + 1)
        for i in range(-1, 2):
            if i == 0:
                label = _('This Week')
            elif i == 1:
                label = _('Future')
            else:
                start_week = first_day_of_week + timedelta(days=i * 7)
                end_week = start_week + timedelta(days=6)
                if start_week.month == end_week.month:
                    label = str(start_week.day) + '-' + str(end_week.day) + ' ' + \
                            format_date(end_week, 'MMM', locale=locale)
                else:
                    label = format_date(start_week, 'd MMM', locale=locale) + '-' + \
                            format_date(end_week, 'd MMM', locale=locale)
            data.append({
                'label': label,
                'value': 0.0,
                'type': 'past' if i < 0 else 'future'
            })

        select_sql_clause = """SELECT COUNT(*) as total FROM """ + res_model + """ where invoice_type = %(invoice_type)s """
        query = ''
        start_date = (first_day_of_week + timedelta(days=-7))
        for i in range(0, 4):
            if i == 0:
                query += "(" + select_sql_clause + " and " + fecthDate + " < '" + \
                         start_date.strftime(DF) + "')"
            elif i == 3:
                query += " UNION ALL (" + select_sql_clause + " and date >= '" + \
                         start_date.strftime(DF) + "')"
            else:
                next_date = start_date + timedelta(days=7)
                query += " UNION ALL (" + select_sql_clause + " and " + fecthDate + " >= '" + \
                         start_date.strftime(DF) + "' and " + fecthDate + " < '" + \
                         next_date.strftime(DF) + "')"
                start_date = next_date

        self.env.cr.execute(query, {'invoice_type': self.invoice_type})
        query_results = self.env.cr.dictfetchall()
        for index in range(0, len(query_results)):
            total = str(query_results[index].get('total'))
            total = total.split('L')
            if int(total[0]) > 0:
                data[index]['value'] = total[0]

        color = '#6e4287'
        graphData = [{
            'values': data,
            'area': True,
            'title': '',
            'key': invoice_type.upper(),
            'color': color
        }]
        return graphData
