import csv
import io
import base64
from urllib.parse import unquote_plus

from odoo import api, models


def _unescape(text):
    try:
        text = unquote_plus(text.encode('utf8'))
        return text
    except Exception as e:
        return text


class ExportCsvWizard(models.TransientModel):
    _name = "export.csv.wizard"

    def create_attachment(self, data, invoice_type, gst_invoice_name):
        attachment = False
        base64Data = base64.b64encode(data.encode('utf-8'))
        store_fname = '{}_{}.csv'.format(invoice_type, gst_invoice_name)
        try:
            res_id = 0
            if self._context.get('gst_id'):
                res_id = self._context.get('gst_id')
            attachment = self.env['ir.attachment'].create({
                'datas': base64Data,
                'type': 'binary',
                'res_model': 'gst.return.tool',
                'res_id': res_id,
                'db_datas': store_fname,
                'store_fname': store_fname,
                'name': store_fname
            }
            )
        except ValueError:
            return attachment
        return attachment

    def wizard_generate_csv(self, data, invoice_type, gst_invoice_name, gst_return_type):
        attachment = False
        if data:
            file = io.StringIO()
            writer = csv.writer(file, quoting=csv.QUOTE_NONE, escapechar='\\')
            if invoice_type == 'b2b':
                data_cols = self.env['data.csv.wizard'].b2b_data_create(gst_return_type)
                writer.writerow(data_cols)
            elif invoice_type == 'b2bur':
                data_cols = self.env['data.csv.wizard'].b2bur_data_create()
                writer.writerow(data_cols)
            elif invoice_type == 'b2cl':
                data_cols = self.env['data.csv.wizard'].b2cl_data_create()
                writer.writerow(data_cols)
            elif invoice_type == 'b2cs':
                data_cols = self.env['data.csv.wizard'].b2cs_data_create()
                writer.writerow(data_cols)
            elif invoice_type == 'imps':
                data_cols = self.env['data.csv.wizard'].import_imps_data_create()
                writer.writerow(data_cols)
            elif invoice_type == 'impg':
                data_cols = self.env['data.csv.wizard'].import_impg_data_create()
                writer.writerow(data_cols)
            elif invoice_type == 'export':
                data_cols = self.env['data.csv.wizard'].export_data_create()
                writer.writerow(data_cols)
            elif invoice_type == 'hsn':
                data_cols = self.env['data.csv.wizard'].HSN_data_create()
                writer.writerow(data_cols)
            for read_line in data:
                writer.writerow([_unescape(name) for name in read_line])
            file.seek(0)
            data = file.read()
            file.close()
            attachment = self.create_attachment(data, invoice_type, gst_invoice_name)
        return attachment

    @api.model
    def export_csv_invoices(self, active_ids, invoice_type, gst_invoice_name, gst_return_type):
        if invoice_type == 'import':
            import_imps_data = self.get_invoice(active_ids, 'imps', gst_return_type)
            import_data = import_imps_data[0]
            import_imps_attachment = self.wizard_generate_csv(import_data, 'imps', gst_invoice_name, gst_return_type)
            import_imps_json_data = import_imps_data[1]
            import_impg_data = self.get_invoice(active_ids, 'impg', gst_return_type)
            import_data = import_impg_data[0]
            import_impg_attachment = self.wizard_generate_csv(import_data, 'impg', gst_invoice_name, gst_return_type)
            import_impg_json_data = import_impg_data[1]
            return [[import_imps_attachment, import_imps_json_data], [import_impg_attachment, import_impg_json_data]]
        export_csv = self.get_invoice(active_ids, invoice_type, gst_return_type)
        import_data = export_csv[0]
        json_data = export_csv[1]
        attachment = self.wizard_generate_csv(import_data, invoice_type, gst_invoice_name, gst_return_type)
        return [attachment, json_data]

    def get_invoice(self, active_ids, invoice_type, gst_return_type):
        invoice_data = []
        json_data = []
        count = 0
        context = dict(self._context or {})
        data_b2cs_dict = {}
        json_data_b2cs_dict = {}
        json_data_b2cl_dict = {}
        data_b2bur_dict = {}
        data_b2b_dict = {}
        hsn_dict = {}
        hsn_data_dict = {}
        reverse_charge_set = 'N'
        if context.get('gst_id'):
            res_id = context.get('gst_id')
            gst_obj = self.env['gst.return.tool'].browse(res_id)
            if gst_obj.reverse_charge:
                reverse_charge_set = 'Y'
        for active_id in active_ids:
            data_invoice = {}
            invoice_obj = self.env['account.move'].browse(active_id)
            reverse_charge_status = 'Y' if invoice_obj.reverse_charge else 'N' if reverse_charge_set == 'N' else reverse_charge_set
            invoice_export_type = invoice_obj.l10n_in_export_type or 'regular'
            json_invoice_type = 'R'
            if invoice_export_type == 'sez_with_igst':
                json_invoice_type = 'SEWP'
            elif invoice_export_type == 'sez_without_igst':
                json_invoice_type = 'SEWOP'
            elif invoice_export_type == 'deemed':
                json_invoice_type = 'DE'
            elif invoice_export_type == 'sale_bonded':
                json_invoice_type = 'CBW'
            currency = invoice_obj.currency_id
            gst_invoice_id = invoice_obj.name or ''
            if gst_return_type == 'gstr2':
                gst_invoice_id = invoice_obj.ref or ''
            if len(gst_invoice_id) > 16:
                gst_invoice_id = gst_invoice_id[0:16]
            date_of_invoice = invoice_obj.invoice_date
            gst_invoice_id_date = date_of_invoice.strftime('%d-%m-%Y')
            date_of_invoice = date_of_invoice.strftime('%d-%b-%Y')
            gst_total_amount = invoice_obj.amount_total
            if currency.name != 'INR':
                gst_total_amount = gst_total_amount * currency.rate
            invoice_obj.inr_total = gst_total_amount
            gst_total_amount = round(gst_total_amount, 2)
            state = invoice_obj.partner_id.state_id
            code = state.l10n_in_tin or 0
            code = _unescape(state.l10n_in_tin)
            state_name_get = _unescape(state.name)
            state_name = "{}-{}".format(code, state_name_get)
            data = []
            if invoice_type == 'b2b':
                customerName = invoice_obj.partner_id.name
                data_invoice = {
                    "inum": gst_invoice_id,
                    "idt": date_of_invoice,
                    "val": gst_total_amount,
                    "pos": code,
                    "reverse_charge": reverse_charge_status,
                    "inv_typ": json_invoice_type
                }
                if gst_return_type == 'gstr1':
                    data_invoice['etin'] = ""
                    data_invoice['diff_percent'] = 0.0
                gstrData = [invoice_obj.l10n_in_partner_vat, gst_invoice_id, date_of_invoice, gst_total_amount, state_name,
                            reverse_charge_status, 'Regular']
                if gst_return_type == 'gstr1':
                    gstrData = [invoice_obj.l10n_in_partner_vat, customerName, gst_invoice_id, date_of_invoice, gst_total_amount,
                                state_name, reverse_charge_status, 0.0, invoice_export_type, '']
                data.extend(gstrData)
                get_gst_invoice_data = self.env['wizard.gst.invoice'].get_gst_invoice_lines(invoice_obj, invoice_type, data, gst_return_type)
                data = get_gst_invoice_data[0]
                data_invoice['itms'] = get_gst_invoice_data[1]
                data_invoice['idt'] = gst_invoice_id_date
                if data_b2b_dict.get(invoice_obj.l10n_in_partner_vat):
                    data_b2b_dict[invoice_obj.l10n_in_partner_vat].append(data_invoice)
                else:
                    data_b2b_dict[invoice_obj.l10n_in_partner_vat] = [data_invoice]
            elif invoice_type == 'b2bur':
                supply_state = 'INTER'
                sply_type = 'Inter State'
                if invoice_obj.partner_id.state_id.code != self.company_id.state_id.code:
                    supply_state = 'INTRA'
                    sply_type = 'Intra State'
                data_invoice = {
                    "inum": gst_invoice_id,
                    "idt": date_of_invoice,
                    "val": gst_total_amount,
                    "pos": code,
                    "supply_state": supply_state
                }
                vendor_name = invoice_obj.partner_id.name
                data.extend([vendor_name, gst_invoice_id, date_of_invoice, gst_total_amount, state_name, sply_type])
                get_gst_invoice_data = self.env['wizard.gst.invoice'].get_gst_invoice_lines(invoice_obj, invoice_type, data, gst_return_type)
                data = get_gst_invoice_data[0]
                data_invoice['itms'] = get_gst_invoice_data[1]
                data_invoice['idt'] = gst_invoice_id_date
                if data_b2bur_dict.get(vendor_name):
                    data_b2bur_dict[vendor_name].append(data_invoice)
                else:
                    data_b2bur_dict[vendor_name] = [data_invoice]

            elif invoice_type == 'b2cl':
                data_invoice = {"inum": gst_invoice_id, "idt": date_of_invoice, "val": gst_total_amount, "etin": "",
                                'diff_percent': 0.0}
                data.extend([gst_invoice_id, date_of_invoice, gst_total_amount, state_name, 0.0])
                get_gst_invoice_data = self.env['wizard.gst.invoice'].get_gst_invoice_lines(invoice_obj, invoice_type, data, gst_return_type)
                data = get_gst_invoice_data[0]
                data_invoice['itms'] = get_gst_invoice_data[1]
                data_invoice['idt'] = gst_invoice_id_date
                if json_data_b2cl_dict.get(code):
                    json_data_b2cl_dict[code].append(data_invoice)
                else:
                    json_data_b2cl_dict[code] = [data_invoice]
            elif invoice_type == 'b2cs':
                data_invoice = {
                    "pos": code
                }
                b2b_data = ['OE', state_name]
                get_gst_invoice_data = self.env['wizard.gst.invoice'].get_gst_invoice_lines(invoice_obj, invoice_type, b2b_data, gst_return_type)
                b2b_data = get_gst_invoice_data[0]
                rateDataDict = get_gst_invoice_data[2]
                rateJsonDict = get_gst_invoice_data[3]
                if data_b2cs_dict.get(state_name):
                    for key in rateDataDict.keys():
                        if data_b2cs_dict.get(state_name).get(key):
                            for key1 in rateDataDict.get(key).keys():
                                if data_b2cs_dict.get(state_name).get(key).get(key1):
                                    data_b2cs_dict.get(state_name).get(key)[key1] = data_b2cs_dict.get(state_name).get(key)[
                                                                                     key1] + rateDataDict.get(key)[key1]
                                else:
                                    data_b2cs_dict.get(state_name).get(key)[key1] = rateDataDict.get(key)[key1]
                        else:
                            data_b2cs_dict.get(state_name)[key] = rateDataDict[key]
                else:
                    data_b2cs_dict[state_name] = rateDataDict
                if json_data_b2cs_dict.get(code):
                    for key in rateJsonDict.keys():
                        if json_data_b2cs_dict.get(code).get(key):
                            for key1 in rateJsonDict.get(key).keys():
                                if json_data_b2cs_dict.get(code).get(key).get(key1):
                                    if key1 in ['rate', 'supply_state', 'typ']:
                                        continue
                                    json_data_b2cs_dict.get(code).get(key)[key1] = json_data_b2cs_dict.get(code).get(key)[
                                                                                    key1] + rateJsonDict.get(key)[key1]
                                    json_data_b2cs_dict.get(code).get(key)[key1] = round(
                                        json_data_b2cs_dict.get(code).get(key)[key1], 2)
                                else:
                                    json_data_b2cs_dict.get(code).get(key)[key1] = rateJsonDict.get(key)[key1]
                        else:
                            json_data_b2cs_dict.get(code)[key] = rateJsonDict[key]
                else:
                    json_data_b2cs_dict[code] = rateJsonDict
                if get_gst_invoice_data[1]:
                    data_invoice.update(get_gst_invoice_data[1][0])
            elif invoice_type == 'imps':
                state = self.env['res.users'].browse(self._uid).company_id.state_id
                code = _unescape(state.l10n_in_tin) or 0
                state_name_get = _unescape(state.name)
                state_name = "{}-{}".format(code, state_name_get)
                data_invoice = {
                    "inum": gst_invoice_id,
                    "idt": date_of_invoice,
                    "ival": gst_total_amount,
                    "pos": code
                }
                vendor_name = invoice_obj.partner_id.name
                data.extend([gst_invoice_id, date_of_invoice, gst_total_amount, state_name])
                get_gst_invoice_data = self.env['wizard.gst.invoice'].get_gst_invoice_lines(invoice_obj, invoice_type, data, gst_return_type)
                data = get_gst_invoice_data[0]
                data_invoice['itms'] = get_gst_invoice_data[1]
                data_invoice['idt'] = gst_invoice_id_date
                json_data.append(data_invoice)
            elif invoice_type == 'impg':
                gstin_number = self.env['res.users'].browse(self._uid).company_id.vat
                portcode = ''
                if invoice_obj.l10n_in_shipping_port_code_id:
                    portcode = invoice_obj.l10n_in_shipping_port_code_id.name
                data_invoice = {
                    "gst_invoice_id_impg": gst_invoice_id,
                    "date_impg": gst_invoice_id_date,
                    "total_impg": gst_total_amount,
                    "port_code": portcode,
                    "stin": gstin_number,
                    'is_sez': 'Y'
                }
                vendor_name = invoice_obj.partner_id.name
                data.extend([portcode, gst_invoice_id, date_of_invoice, gst_total_amount, 'Imports', gstin_number])
                get_gst_invoice_data = self.env['wizard.gst.invoice'].get_gst_invoice_lines(invoice_obj, invoice_type, data, gst_return_type)
                data = get_gst_invoice_data[0]
                data_invoice['itms'] = get_gst_invoice_data[1]
                json_data.append(data_invoice)
            elif invoice_type == 'export':
                portcode = ''
                if invoice_obj.l10n_in_shipping_port_code_id:
                    portcode = invoice_obj.l10n_in_shipping_port_code_id.name
                data_invoice = {"inum": gst_invoice_id, "idt": date_of_invoice, "val": gst_total_amount, "sbpcode": portcode,
                                "sbnum": "", "sbdt": "", 'diff_percent': 0.0}
                data.extend([invoice_obj.export, gst_invoice_id, date_of_invoice, gst_total_amount, portcode, '', '', 0.0])
                get_gst_invoice_data = self.env['wizard.gst.invoice'].get_gst_invoice_lines(invoice_obj, invoice_type, data, gst_return_type)
                data = get_gst_invoice_data[0]
                data_invoice['itms'] = get_gst_invoice_data[1]
                data_invoice['idt'] = gst_invoice_id_date
                json_data.append(data_invoice)
            elif invoice_type == 'hsn':
                get_gst_invoice_data = self.env['gst.hsn.data'].update_HSN_data(invoice_obj, count, hsn_dict, hsn_data_dict)
                data = get_gst_invoice_data[0]
                json_data.extend(get_gst_invoice_data[1])
                hsn_dict = get_gst_invoice_data[2]
                hsn_data_dict = get_gst_invoice_data[3]
                invoice_obj.gst_status = 'ready_upload'
            if data:
                invoice_data.extend(data)
        if json_data_b2cs_dict:
            for pos, val in json_data_b2cs_dict.items():
                for line in val.values():
                    line['pos'] = pos
                    line['diff_percent'] = 0.0
                    json_data.append(line)
        if data_b2cs_dict:
            b2cs_data = []
            for state, data in data_b2cs_dict.items():
                for rate, val in data.items():
                    b2cs_data.append(['OE', state, 0.0, rate, round(val['taxval'], 2), round(val['cess'], 2), ''])
            invoice_data = b2cs_data

        if data_b2b_dict:
            for ctin, inv in data_b2b_dict.items():
                json_data.append({
                    'ctin': ctin,
                    'inv': inv
                })
        if data_b2bur_dict:
            for ctin, inv in data_b2bur_dict.items():
                json_data.append({
                    'inv': inv
                })
        if json_data_b2cl_dict:
            for pos, inv in json_data_b2cl_dict.items():
                json_data.append({
                    'pos': pos,
                    'inv': inv
                })
        if hsn_dict:
            vals = hsn_dict.values()
            hsn_data_top = []
            for val in vals:
                hsn_data_top.extend(val.values())
            invoice_data = hsn_data_top
        if hsn_data_dict:
            vals = hsn_data_dict.values()
            hsn_data_top = []
            for val in vals:
                hsn_data_top.extend(val.values())
            json_data = hsn_data_top
        return [invoice_data, json_data]
