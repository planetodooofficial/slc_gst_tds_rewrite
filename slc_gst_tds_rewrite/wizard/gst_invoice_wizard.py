# -*- coding: utf-8 -*-
from odoo import api, models


class WizardInvoiceGST(models.TransientModel):
    _name = "wizard.gst.invoice"

    def get_invoice_line(self, get_invoice_line, obj_invoice_line, gst_invoice_obj, invoice_type):
        invoice_line_data = []
        invoice_line_data_json = {}
        amount_taxed = 0.0
        rate = 0.0
        amt_rate = 0.0
        currency = gst_invoice_obj.currency_id or None
        price = obj_invoice_line.price_subtotal / obj_invoice_line.quantity if obj_invoice_line.quantity > 0 else 0.0
        obj_rate = obj_invoice_line.tax_ids
        if obj_rate:
            for obj_rate in obj_rate:
                if obj_rate.amount_type == "group":
                    for childObj in obj_rate.children_tax_ids:
                        rate = childObj.amount * 2
                        invoice_line_data.append(rate)
                        break
                else:
                    rate = obj_rate.amount
                    invoice_line_data.append(rate)
                break
            computed_tax_amount = self.env['wizard.tax.gst'].compute_taxed_amount(
                obj_rate, price, currency, obj_invoice_line, gst_invoice_obj)
            amt_rate = computed_tax_amount[1]
            amt_rate = round(amt_rate, 2)
            amount_taxed = computed_tax_amount[0]
            invoice_line_data_json = self.env['wizard.tax.gst'].gst_tax_data(
                gst_invoice_obj, obj_invoice_line, obj_rate, amount_taxed, invoice_type)
        else:
            amt_rate = obj_invoice_line.price_subtotal
            amt_rate = amt_rate
            if currency.name != 'INR':
                amt_rate = amt_rate * currency.rate
            amt_rate = round(amt_rate, 2)
            invoice_line_data.append(0)
            invoice_line_data_json = self.env['wizard.tax.gst'].gst_tax_data(
                gst_invoice_obj, obj_invoice_line, False, amount_taxed, invoice_type)
        data = get_invoice_line + invoice_line_data
        return [data, invoice_line_data_json, rate, amt_rate]

    def get_gst_invoice_lines(self, gst_invoice_obj, invoice_type, data, gst_return_type=''):
        data_json = []
        count = 0
        get_rate_data = {}
        rate_data = {}
        get_rate_data_json = {}
        check_itc_eligible = 'Ineligible'
        context = dict(self._context or {})
        if gst_return_type == 'gstr2':
            if context.get('gst_id'):
                res_id = context.get('gst_id')
                current_obj = self.env['gst.return.tool'].browse(res_id)
                check_itc_eligible = current_obj.avail_itc_eligible
            if check_itc_eligible == 'Ineligible':
                check_itc_eligible = gst_invoice_obj.avail_itc_eligible
        for obj_invoice_line in gst_invoice_obj.invoice_line_ids:
            if obj_invoice_line.product_id:
                if obj_invoice_line.product_id.type == 'service':
                    if invoice_type == 'impg':
                        continue
                else:
                    if invoice_type == 'imps':
                        continue
            else:
                if invoice_type == 'impg':
                    continue
            get_invoice_line = self.get_invoice_line(data, obj_invoice_line, gst_invoice_obj, invoice_type)
            if get_invoice_line:
                rate = get_invoice_line[2]
                amt_rate = get_invoice_line[3]
                if get_invoice_line[1]:
                    get_invoice_line[1]['tax_value'] = amt_rate
                if gst_return_type == 'gstr2':
                    igst = get_invoice_line[1].get('gst_round_amt') or 0.0
                    cgst = get_invoice_line[1].get('cgst_amt') or 0.0
                    sgst = get_invoice_line[1].get('sgst_amt') or 0.0
                    if rate not in rate_data.keys():
                        get_rate_data[rate] = {
                            'taxval': amt_rate,
                            'igst': igst,
                            'cgst': cgst,
                            'sgst': sgst,
                            'cess': 0.0
                        }
                    else:
                        get_rate_data[rate]['taxval'] = get_rate_data[rate]['taxval'] + amt_rate
                        get_rate_data[rate]['igst'] = get_rate_data[rate]['igst'] + igst
                        get_rate_data[rate]['cgst'] = get_rate_data[rate]['cgst'] + cgst
                        get_rate_data[rate]['sgst'] = get_rate_data[rate]['sgst'] + sgst
                        get_rate_data[rate]['cess'] = get_rate_data[rate]['cess'] + 0.0
                if gst_return_type == 'gstr1':
                    if rate not in rate_data.keys():
                        get_rate_data[rate] = {
                            'taxval': amt_rate,
                            'cess': 0.0
                        }
                    else:
                        get_rate_data[rate]['taxval'] = get_rate_data[rate]['taxval'] + amt_rate
                        get_rate_data[rate]['cess'] = get_rate_data[rate]['cess'] + 0.0
                if rate not in get_rate_data_json.keys():
                    get_rate_data_json[rate] = get_invoice_line[1]
                else:
                    for key in get_invoice_line[1].keys():
                        if key in ['gst_amt', 'supply_state', 'typ', 'itc_eligibility']:
                            continue
                        if get_rate_data_json[rate].get(key):
                            get_rate_data_json[rate][key] = get_rate_data_json[rate][key] + get_invoice_line[1][key]
                            get_rate_data_json[rate][key] = round(get_rate_data_json[rate][key], 2)
                        else:
                            get_rate_data_json[rate][key] = get_invoice_line[1][key]
                invoice_line = []
                if gst_return_type == 'gstr1':
                    invoice_line = get_invoice_line[0] + [get_rate_data[rate]['taxval']]
                if gst_return_type == 'gstr2':
                    if invoice_type in ['imps', 'impg']:
                        invoice_line = get_invoice_line[0] + \
                                       [get_rate_data[rate]['taxval'],
                                        get_rate_data[rate]['igst']
                                        ]
                    else:
                        invoice_line = get_invoice_line[0] + [
                            get_rate_data[rate]['taxval'],
                            get_rate_data[rate]['igst'],
                            get_rate_data[rate]['cgst'],
                            get_rate_data[rate]['sgst']
                        ]
                if invoice_type == 'b2b':
                    if gst_return_type == 'gstr1':
                        invoice_line = invoice_line + [0.0]
                    if gst_return_type == 'gstr2':
                        if check_itc_eligible != 'Ineligible':
                            invoice_line = invoice_line + [0.0] + [check_itc_eligible] + [
                                get_rate_data[rate]['igst']
                            ] + [get_rate_data[rate]['cgst']] + [
                                get_rate_data[rate]['sgst']
                            ] + [get_rate_data[rate]['cess']]
                        else:
                            invoice_line = invoice_line + [0.0] + [check_itc_eligible] + [0.0] * 4

                elif invoice_type == 'b2bur':
                    if check_itc_eligible != 'Ineligible':
                        invoice_line = invoice_line + [0.0] + [check_itc_eligible] + [
                            get_rate_data[rate]['igst']
                        ] + [get_rate_data[rate]['cgst']] + [
                            get_rate_data[rate]['sgst']
                        ] + [get_rate_data[rate]['cess']]
                    else:
                        invoice_line = invoice_line + [0.0] + [check_itc_eligible] + [0.0] * 4
                elif invoice_type in ['imps', 'impg']:
                    if check_itc_eligible != 'Ineligible':
                        invoice_line = invoice_line + [0.0] + [check_itc_eligible] + [
                            get_rate_data[rate]['igst']
                        ] + [get_rate_data[rate]['cess']]
                    else:
                        invoice_line = invoice_line + [0.0] + [check_itc_eligible] + [0.0] + [0.0]
                elif invoice_type in ['b2cs', 'b2cl']:
                    invoice_line = invoice_line + [0.0, '']
                    if invoice_type == 'b2cl':
                        bonded_wh = 'Y' if gst_invoice_obj.l10n_in_export_type == 'sale_bonded' else 'N'
                        invoice_line = invoice_line + [bonded_wh]
                rate_data[rate] = invoice_line
        import_data = rate_data.values()
        if get_rate_data_json:
            for json_data in get_rate_data_json.values():
                count = count + 1
                if invoice_type == 'b2b' and gst_return_type == 'gstr2':
                    data_json.append({
                        "num": count,
                        'itm_det': json_data,
                        "itc": {
                            "itc_eligibility": "no",
                            "tax_invoice": 0.0,
                            "tx_s": 0.0,
                            "tx_c": 0.0,
                            "tax_cess": 0.0
                        }
                    })
                elif invoice_type == 'b2bur':
                    data_json.append({
                        "num": count,
                        'itm_det': json_data,
                        "itc": {
                            "itc_eligibility": "no",
                            "tax_invoice": 0.0,
                            "tx_s": 0.0,
                            "tx_c": 0.0,
                            "tax_cess": 0.0
                        }
                    })
                elif invoice_type in ['imps', 'impg']:
                    data_json.append({
                        "num": count,
                        'itm_det': json_data,
                        "itc": {
                            "itc_eligibility": "no",
                            "tax_invoice": 0.0,
                            "tax_cess": 0.0
                        }
                    })
                else:
                    data_json.append({"num": count, 'itm_det': json_data})
        return [import_data, data_json, get_rate_data, get_rate_data_json]

