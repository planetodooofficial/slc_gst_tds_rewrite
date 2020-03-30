import base64
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError


def find_gst_return_type():
    return [('gstr1', 'GSTR1'), ('gstr2', 'GSTR2')]


def change_invoice_currency(gst_invoice_objs):
    for gst_invoice_obj in gst_invoice_objs:
        amount_total = gst_invoice_obj.amount_total_signed
        if gst_invoice_obj.currency_id.name != 'INR':
            amount_total = amount_total * gst_invoice_obj.currency_id.rate
        gst_invoice_obj.amount_total = amount_total
    return True


class GSTReturn(models.Model):
    _name = "gst.return.tool"
    _inherit = ['mail.thread']

    name = fields.Char(string='GST Invoice')
    gst_return_type = fields.Selection(string='GST Return Type',
                                       selection=lambda self, *args, **kwargs: find_gst_return_type(*args, **kwargs),
                                       default='gstr1')
    reverse_charge = fields.Boolean(string='Reverse Charge')
    fy_id = fields.Many2one('account.period', tracking=True, string='Fiscal Period')
    status = fields.Selection(
        [('yet_to_upload', 'Yet To Upload'),
         ('ready_upload', 'Ready to upload'),
         ('upload_complete', 'Upload Completed'), ('filed', 'Filed')],
        string='Status', default="yet_to_upload", tracking=True)
    current_gross_turnover = fields.Float(string='Current Gross Turnover', tracking=True)
    gross_turnover = fields.Float(string='Gross Turnover', tracking=True, help="Gross Turnover till current date")
    start_date = fields.Date(string='Date From')
    end_date = fields.Date(string='Date To', help="Date end range for filter")
    gst_lines = fields.Many2many('account.move', string='Customer Invoices')
    count_attachment = fields.Integer(string=' Total Attachments', compute='compute_attachment_count',
                                      readonly=True)
    count_invoice = fields.Integer(string='Invoice Count', compute='compute_invoice_count',
                                    readonly=True)
    avail_itc_eligible = fields.Selection([
        ('Inputs', 'Inputs'),
        ('Capital goods', 'Capital goods'),
        ('Input services', 'Input services'),
        ('Ineligible', 'Ineligible'),
    ], string='Eligibility to avail ITC', default='Ineligible')
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id)
    b2b_attachment = fields.Many2one('ir.attachment')
    b2bur_attachment = fields.Many2one('ir.attachment')
    b2cs_attachment = fields.Many2one('ir.attachment')
    b2cl_attachment = fields.Many2one('ir.attachment')
    export_attachment = fields.Many2one('ir.attachment')
    imps_attachment = fields.Many2one('ir.attachment')
    impg_attachment = fields.Many2one('ir.attachment')
    hsn_attachment = fields.Many2one('ir.attachment')
    json_attachment = fields.Many2one('ir.attachment')

    @api.depends('b2b_attachment', 'b2cs_attachment', 'b2bur_attachment',
                 'b2cl_attachment', 'imps_attachment', 'impg_attachment',
                 'export_attachment', 'hsn_attachment', 'json_attachment')
    def compute_attachment_count(self):
        for attachment in self:
            attachments = []
            if self.b2b_attachment:
                attachments.append(self.b2b_attachment.id)
            if self.b2bur_attachment:
                attachments.append(self.b2bur_attachment.id)
            if self.b2cs_attachment:
                attachments.append(self.b2cs_attachment.id)
            if self.b2cl_attachment:
                attachments.append(self.b2cl_attachment.id)
            if self.imps_attachment:
                attachments.append(self.imps_attachment.id)
            if self.impg_attachment:
                attachments.append(self.impg_attachment.id)
            if self.export_attachment:
                attachments.append(self.export_attachment.id)
            if self.hsn_attachment:
                attachments.append(self.hsn_attachment.id)
            if self.json_attachment:
                attachments.append(self.json_attachment.id)

            attachment.update({'count_attachment': len(attachments)})

    @api.depends('gst_lines')
    def compute_invoice_count(self):
        for invoice in self:
            invoices = []
            if invoice.gst_lines:
                invoices = invoice.gst_lines.ids
            invoice.update({'count_invoice': len(invoices)})

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('gst.return.tool')
        res = super(GSTReturn, self).create(vals)
        return res

    def unlink(self):
        for gst in self:
            if gst.status != "yet_to_upload":
                raise UserError("Already generated invoices cannot be deleted")
        res = super(GSTReturn, self).unlink()
        return res

    def write(self, vals):
        res = super(GSTReturn, self).write(vals)
        for gst in self:
            if gst.start_date and gst.end_date:
                if gst.fy_id.start_period > gst.start_date:
                    if gst.fy_id.start_period > gst.end_date:
                        if gst.fy_id.end_period < gst.end_date:
                            if gst.fy_id.end_period < gst.start_date:
                                raise UserError("Date should be within selected period")
                if gst.start_date > gst.end_date:
                    raise UserError("End date cannot be before start date")
        return res

    def onchange(self, values, field_name, field_onchange):
        context = dict(self._context or {})
        context['current_id'] = values.get('id')
        res = super(GSTReturn, self.with_context(context)).onchange(values, field_name, field_onchange)
        return res

    def reset_invoice(self):
        gst_lines = self.gst_lines
        invoice_count = len(gst_lines)
        if self.b2b_attachment:
            self.b2b_attachment.unlink()
        if self.b2bur_attachment:
            self.b2bur_attachment.unlink()
        if self.b2cl_attachment:
            self.b2cl_attachment.unlink()
        if self.b2cs_attachment:
            self.b2cs_attachment.unlink()
        if self.hsn_attachment:
            self.hsn_attachment.unlink()
        if self.imps_attachment:
            self.imps_attachment.unlink()
        if self.impg_attachment:
            self.impg_attachment.unlink()
        if self.export_attachment:
            self.export_attachment.unlink()
        if self.json_attachment:
            self.json_attachment.unlink()
        self.status = 'yet_to_upload'
        for gst in gst_lines:
            gst.invoice_type_status = 'yet_to_upload'
        self.fetch_invoice_details()
        body = '<b>RESET </b>: {} GST Invoices'.format(invoice_count)
        self.message_post(body=_(body), subtype='mail.mt_comment')
        return True

    def get_invoice_action(self):
        get_invoice = self.mapped('gst_lines')
        action = self.env.ref('slc_gst_tds_rewrite.customer_invoice_list_action').read()[0]
        if len(get_invoice) > 1:
            action['domain'] = [('id', 'in', get_invoice.ids)]
        elif len(get_invoice) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = get_invoice.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_view_attachment(self):
        get_attachments = []
        if self.b2b_attachment:
            get_attachments.append(self.b2b_attachment.id)
        if self.b2bur_attachment:
            get_attachments.append(self.b2bur_attachment.id)
        if self.b2cs_attachment:
            get_attachments.append(self.b2cs_attachment.id)
        if self.b2cl_attachment:
            get_attachments.append(self.b2cl_attachment.id)
        if self.imps_attachment:
            get_attachments.append(self.imps_attachment.id)
        if self.export_attachment:
            get_attachments.append(self.export_attachment.id)
        if self.hsn_attachment:
            get_attachments.append(self.hsn_attachment.id)
        if self.json_attachment:
            get_attachments.append(self.json_attachment.id)
        if self.impg_attachment:
            get_attachments.append(self.impg_attachment.id)

        action = self.env.ref('slc_gst_tds_rewrite.gst_attachments_action').read()[0]
        if len(get_attachments) > 1:
            action['domain'] = [('id', 'in', get_attachments)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.onchange('fy_id', 'start_date', 'end_date')
    def get_invoices(self):
        domain = {}
        for gst_obj in self:
            add_filter = ()
            context = dict(self._context or {})
            gst_invoice_obj = []
            if context.get('current_id'):
                add_filter = ('id', '!=', context.get('current_id'))
            type_of_invoice = 'out_invoice'
            if gst_obj.gst_return_type == 'gstr2':
                type_of_invoice = 'in_invoice'
            gst_invoice_obj = gst_obj.get_invoice_details(add_filter, type_of_invoice)
            if gst_invoice_obj:
                self.gst_update_lines(gst_invoice_obj)
                domain['gst_lines'] = [('id', 'in', gst_invoice_obj.ids)]
            else:
                domain['gst_lines'] = [('id', 'in', [])]
        return {'domain': domain}

    def fetch_invoice_details(self):
        context = dict(self._context or {})
        gst_invoice_obj = self.with_context(context).get_invoice_details(('id', '!=', self.id), 'out_invoice')
        self.gst_lines = [(6, 0, gst_invoice_obj.ids)]
        if gst_invoice_obj:
            change_invoice_currency(gst_invoice_obj)
            self.gst_update_lines(gst_invoice_obj)
        return True

    def get_vendor_invoice(self):
        gst_invoice_obj = self.with_context(dict(self._context or {})).get_invoice_details(('id', '!=', self.id), 'in_invoice')
        self.gst_lines = [(6, 0, gst_invoice_obj.ids)]
        if gst_invoice_obj:
            change_invoice_currency(gst_invoice_obj)
            self.gst_update_lines(gst_invoice_obj)
        return True

    def gst_update_lines(self, gst_invoice_objs):
        for gst_invoice_obj in gst_invoice_objs:
            if gst_invoice_obj.type == 'in_invoice':
                if gst_invoice_obj.partner_id.country_id.code == 'IN':
                    if gst_invoice_obj.partner_id.vat:
                        gst_invoice_obj.invoice_type = 'b2b'
                    else:
                        gst_invoice_obj.invoice_type = 'b2bur'
                else:
                    gst_invoice_obj.invoice_type = 'import'
            else:
                if gst_invoice_obj.partner_id.country_id.code == 'IN':
                    if gst_invoice_obj.partner_id.vat:
                        gst_invoice_obj.invoice_type = 'b2b'
                    elif gst_invoice_obj.amount_total >= 250000 and gst_invoice_obj.partner_id.state_id.code != self.env['res.users'].browse(self._uid).company_id.state_id.code:
                        gst_invoice_obj.invoice_type = 'b2cl'
                        if not gst_invoice_obj.l10n_in_export_type:
                            gst_invoice_obj.l10n_in_export_type = 'regular'
                    else:
                        gst_invoice_obj.invoice_type = 'b2cs'
                else:
                    gst_invoice_obj.invoice_type = 'export'
                    gst_invoice_obj.export = 'without_pay'
        return True

    def get_invoice_details(self, extra_filter=(), invoice_type=''):
        gst_invoice_objs = []
        gst_objs = self.search([])
        if extra_filter:
            gst_objs = self.search([extra_filter])
        invoice_obj = []
        for gst_obj in gst_objs:
            invoice_obj.extend(gst_obj.gst_lines.ids)
        if self.fy_id:
            add_filter = [
                ('invoice_date', '>=', self.fy_id.start_period),
                ('invoice_date', '<=', self.fy_id.end_period),
                ('invoice_type_status', '=', 'yet_to_upload'),
                ('type', '=', invoice_type),
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'posted'),
            ]
            if not self.start_date:
                self.start_date = self.fy_id.start_period
                self.end_date = self.fy_id.end_period
            if self.start_date and self.end_date:
                if self.fy_id.start_period > self.start_date \
                        or self.fy_id.start_period > self.end_date \
                        or self.fy_id.end_period < self.end_date \
                        or self.fy_id.end_period < self.start_date:
                    raise UserError("Date should be within the selected period")
                if self.start_date > self.end_date:
                    raise UserError("End date should not be before start date")
                add_filter.append(('invoice_date', '>=', self.start_date))
                add_filter.append(('invoice_date', '<=', self.end_date))
            if invoice_obj:
                add_filter.append(('id', 'not in', invoice_obj))
            gst_invoice_objs = self.env['account.move'].search(add_filter)
        return gst_invoice_objs

    def generate_documents(self):
        gst_invoice_objs = self.gst_lines
        if gst_invoice_objs:
            name = self.name
            invoice_type_dict = {}
            invoice_obj = gst_invoice_objs.ids
            for gst_invoice_obj in gst_invoice_objs:
                if invoice_type_dict.get(gst_invoice_obj.invoice_type):
                    invoice_type_dict.get(gst_invoice_obj.invoice_type).append(gst_invoice_obj.id)
                else:
                    invoice_type_dict[gst_invoice_obj.invoice_type] = [gst_invoice_obj.id]
            gstin_number = self.env['res.users'].browse(self._uid).company_id.vat
            fiscal_period = self.fy_id.code
            if fiscal_period:
                fiscal_period = fiscal_period.replace('/', '')
            json_data = {
                "gstin_number": gstin_number,
                "fiscal_period": fiscal_period,
                "gross_turnover": self.gross_turnover,
                "current_gross_turnover": self.current_gross_turnover,
            }
            context = dict(self._context or {})
            context['gst_id'] = self.id
            attachment_type = []
            if self.b2b_attachment:
                attachment_type.append('b2b')
            if self.b2bur_attachment:
                attachment_type.append('b2bur')
            if self.b2cs_attachment:
                attachment_type.append('b2cs')
            if self.b2cl_attachment:
                attachment_type.append('b2cl')
            if self.export_attachment:
                attachment_type.append('export')
            if self.imps_attachment:
                attachment_type.append('imps')
            if self.impg_attachment:
                attachment_type.append('impg')
            gst_return_type = self.gst_return_type
            for invoice_type, active_ids in invoice_type_dict.items():
                if invoice_type in attachment_type:
                    continue
                export_csv = self.env['export.csv.wizard'].with_context(
                    context).export_csv_invoices(active_ids, invoice_type, name, gst_return_type)
                attachment = export_csv[0]
                gst_json_data = export_csv[1]
                if invoice_type == 'b2b':
                    json_data.update({invoice_type: gst_json_data})
                    self.b2b_attachment = attachment.id
                if invoice_type == 'b2bur':
                    json_data.update({invoice_type: gst_json_data})
                    self.b2bur_attachment = attachment.id
                if invoice_type == 'b2cs':
                    self.b2cs_attachment = attachment.id
                    json_data.update({invoice_type: gst_json_data})
                if invoice_type == 'b2cl':
                    json_data.update({invoice_type: gst_json_data})
                    self.b2cl_attachment = attachment.id
                if invoice_type == 'import':
                    import_attachment = attachment[0]
                    import_json_data = attachment[1]
                    import_impg_attachment = gst_json_data[0]
                    import_impg_json_data = gst_json_data[1]
                    json_data.update({
                        'import_json_data': import_json_data,
                        'import_impg_json_data': import_impg_json_data
                    })
                    if import_attachment:
                        self.imps_attachment = import_attachment.id
                    if import_impg_attachment:
                        self.impg_attachment = import_impg_attachment.id
                if invoice_type == 'export':
                    json_data.update(
                        {'export': {
                            "export_type": "without_pay",
                            "invoice": gst_json_data
                        }})
                    self.export_attachment = attachment.id
            if not self.hsn_attachment:
                gst_hsn_data = self.env['export.csv.wizard'].with_context(
                    context).export_csv_invoices(invoice_obj, 'hsn', name, gst_return_type)
                if gst_hsn_data:
                    hsn_attach = gst_hsn_data[0]
                    gst_json_data = gst_hsn_data[1]
                    json_data.update({'hsn': {"data": gst_json_data}})
                    if hsn_attach:
                        self.hsn_attachment = hsn_attach.id
                        self.status = 'ready_upload'
            if not self.json_attachment:
                if json_data:
                    json_data = json.dumps(json_data, indent=4, sort_keys=False)
                    base64Data = base64.b64encode(json_data.encode('utf-8'))
                    json_attach = False
                    try:
                        file_json = "{}.json".format(name)
                        json_attach = self.env['ir.attachment'].create({
                            'datas': base64Data,
                            'type': 'binary',
                            'res_model': 'gst.return.tool',
                            'res_id': self.id,
                            'db_datas': file_json,
                            'store_fname': file_json,
                            'name': file_json
                        })
                    except ValueError:
                        return json_attach
                    if json_attach:
                        self.json_attachment = json_attach.id
        partial = self.env['message.wizard'].create({'text': "The documents are generated successfully"})
        return {
            'name': "GST Status",
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'view_id': self.env.ref('slc_gst_tds_rewrite.wizard_message_form').id,
            'res_id': partial.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
        }

    def upload_status(self):
        partial = self.env['message.wizard'].create({'text': 'GST invoice is uploaded successfully'})
        self.status = 'upload_complete'
        self.status_update('upload_complete')
        return {
            'name': "GST Status",
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'view_id': self.env.ref('slc_gst_tds_rewrite.wizard_message_form').id,
            'res_id': partial.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
        }

    def filed_status(self):
        partial = self.env['message.wizard'].create({'text': 'GST Invoice is filed successfully'})
        self.status = 'filed'
        self.status_update('filed')
        return {
            'name': "GST Status",
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'view_id': self.env.ref('slc_gst_tds_rewrite.wizard_message_form').id,
            'res_id': partial.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
        }

    def status_update(self, updated_status):
        self.gst_lines.write({'invoice_type_status': updated_status})
        return True

    def generate_hsn_csv(self):
        if not self.hsn_attachment:
            self.generate_documents()
        if not self.hsn_attachment:
            raise UserError("HSN is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.hsn_attachment.id,
            'target': 'new',
        }

    def generate_json(self):
        if not self.json_attachment:
            self.generate_documents()
        if not self.json_attachment:
            raise UserError("JSON is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.json_attachment.id,
            'target': 'new',
        }

    def generate_b2b_csv(self):
        if not self.b2b_attachment:
            self.generate_documents()
        if not self.b2b_attachment:
            raise UserError("B2B CSV is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.b2b_attachment.id,
            'target': 'new',
        }

    def generate_b2bur_csv(self):
        if not self.b2bur_attachment:
            self.generate_documents()
        if not self.b2bur_attachment:
            raise UserError("B2BUR CSV is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.b2bur_attachment.id,
            'target': 'new',
        }

    def generate_b2cs_csv(self):
        if not self.b2cs_attachment:
            self.generate_documents()
        if not self.b2cs_attachment:
            raise UserError("B2CS CSV is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.b2cs_attachment.id,
            'target': 'new',
        }

    def generate_b2cl_csv(self):
        if not self.b2cl_attachment:
            self.generate_documents()
        if not self.b2cl_attachment:
            raise UserError("B2CL CSV is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.b2cl_attachment.id,
            'target': 'new',
        }

    def generate_imps_csv(self):
        if not self.imps_attachment:
            self.generate_documents()
        if not self.imps_attachment:
            raise UserError("IMPS CSV is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.imps_attachment.id,
            'target': 'new',
        }

    def generate_impg_csv(self):
        if not self.impg_attachment:
            self.generate_documents()
        if not self.impg_attachment:
            raise UserError("IMPS CSV is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.impg_attachment.id,
            'target': 'new',
        }

    def generate_csv(self):
        if not self.export_attachment:
            self.generate_documents()
        if not self.export_attachment:
            raise UserError("Export CSV is not available")
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=1' % self.export_attachment.id,
            'target': 'new',
        }



