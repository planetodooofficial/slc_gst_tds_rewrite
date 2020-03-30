from odoo import api, fields, models


class InvoiceTypeWizard(models.TransientModel):
    _name = "invoice.type.wizard"

    invoice_type = fields.Selection([('b2b', 'B2B'),
                                     ('b2cl', 'B2CL'),
                                     ('b2cs', 'B2CS'),
                                     ('export', 'Export')],
                                    string='Invoice Type')
    export = fields.Selection([('with_pay', 'WPay'),
                               ('without_pay', 'WoPay')],
                              string='Export')
    avail_itc_eligible = fields.Selection([('Inputs', 'Inputs'),
                                           ('Capital goods', 'Capital goods'),
                                           ('Input services', 'Input services'),
                                           ('Ineligible', 'Ineligible'),
                                           ], string='Eligibility to avail ITC',
                                          )
    reverse_charge = fields.Boolean(string='Reverse Charge')
    portcode_id = fields.Many2one('l10n_in.port.code', 'Port Code')
    invoice_type_status = fields.Selection(
        [('yet_to_upload', 'Not Uploaded'),
         ('ready_upload', 'Ready to upload'),
         ('upload_complete', 'Uploaded to govt'), ('filed', 'Filed')],
        string='GST Status')
    l10n_in_export_type = fields.Selection(
        [
            ('regular', 'Regular'),
            ('deemed', 'Deemed'),
            ('sale_bonded', 'Sale from Bonded WH'),
            ('igst_export', 'Export with IGST'),
            ('sez_with_igst', 'SEZ with IGST payment'),
            ('sez_without_igst', 'SEZ without IGST payment')
        ], string='Export Type', default='regular', required=True
    )

    @api.model
    def change_invoice_status(self):
        res = self.create({})
        context = dict(self._context or {})
        return {
            'name': "Update Invoice",
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'invoice.type.wizard',
            'res_id': res.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': context,
            'domain': '[]',
        }

    def update_invoices(self):
        no_of_records = 0
        for active_id in self._context.get('active_ids'):
            gst_invoice_obj = self.env[self._context.get('active_model')].browse(active_id)
            data = {}
            if self.invoice_type:
                data['invoice_type'] = self.invoice_type
            if self.invoice_type_status:
                data['invoice_type_status'] = self.invoice_type_status
            if self.export:
                data['export'] = self.export
            if self.avail_itc_eligible:
                data['avail_itc_eligible'] = self.avail_itc_eligible
            if self.l10n_in_export_type:
                data['l10n_in_export_type'] = self.l10n_in_export_type
            if self.reverse_charge:
                data['reverse_charge'] = self.reverse_charge
            if self.portcode_id:
                data['l10n_in_shipping_port_code_id'] = self.portcode_id
            if data:
                gst_invoice_obj.write(data)
            no_of_records = no_of_records + 1
        text = 'Successful update of %s record(s).' % no_of_records
        partial = self.env['message.wizard'].create({'text': text})
        return {
            'name': "Information",
            'view_mode': 'form',
            'res_model': 'message.wizard',
            'view_id': self.env.ref('slc_gst_tds_rewrite.wizard_message_form').id,
            'res_id': partial.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
        }
