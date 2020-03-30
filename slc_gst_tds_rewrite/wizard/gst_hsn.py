from odoo import api, fields, models


class GstHsnData(models.TransientModel):
    _name = "gst.hsn.data"
    _description = "GST HSN data"

    def update_HSN_data(self, gst_invoice_obj, count, get_hsn_data={}, hsn_get={}):
        import_data = []
        json_data = []
        currency = gst_invoice_obj.currency_id or None
        context = dict(self._context or {})
        for obj_invoice_line in gst_invoice_obj.invoice_line_ids:
            price = obj_invoice_line.price_subtotal / obj_invoice_line.quantity
            amount_taxed, cgst, sgst, igst = 0.0, 0.0, 0.0, 0.0
            obj_rate = obj_invoice_line.tax_ids
            if obj_rate:
                computed_tax_amount = self.env['wizard.tax.gst'].compute_taxed_amount(
                    obj_rate, price, currency, obj_invoice_line, gst_invoice_obj)
                amt_rate = computed_tax_amount[1]
                amount_taxed = computed_tax_amount[0]
                if currency.name != 'INR':
                    amount_taxed = amount_taxed * currency.rate
                amount_taxed = round(amount_taxed, 2)
                # if gst_invoice_obj.partner_id.country_id.code == 'IN':
                for obj_rate in obj_rate:
                    if obj_rate.amount_type == "group":
                        cgst, sgst = round(amount_taxed / 2, 2), round(amount_taxed / 2, 2)
                    else:
                        igst = round(amount_taxed, 2)
            invoice_line_untaxed_amt = round(obj_invoice_line.price_subtotal, 2)
            if currency.name != 'INR':
                invoice_line_untaxed_amt = round(obj_invoice_line.price_subtotal * currency.rate, 2)
            obj_product = obj_invoice_line.product_id
            hsn_status = 'False'
            if obj_product.l10n_in_hsn_code:
                hsn_status = obj_product.l10n_in_hsn_code.replace('.', '')
            hsn_name = obj_product.name or 'name'
            unit_code = 'OTH'
            if obj_product.uom_id:
                uom = obj_product.uom_id.id
                unit_code_obj = self.env['uom.mapping'].search([('uom', '=', uom)])
                if unit_code_obj:
                    unit_code = unit_code_obj[0].name.code
            invoice_qty = obj_invoice_line.quantity
            invoice_amount_total = invoice_line_untaxed_amt + amount_taxed
            if get_hsn_data.get(hsn_status):
                if get_hsn_data.get(hsn_status).get(hsn_name):
                    if get_hsn_data.get(hsn_status).get(hsn_name).get('qty'):
                        invoice_qty += get_hsn_data.get(hsn_status).get(hsn_name).get('qty')
                        get_hsn_data.get(hsn_status).get(hsn_name)['qty'] = invoice_qty
                    else:
                        get_hsn_data.get(hsn_status).get(hsn_name)['qty'] = invoice_qty
                    if get_hsn_data.get(hsn_status).get(hsn_name).get('val'):
                        invoice_amount_total = round(
                            get_hsn_data.get(hsn_status).get(hsn_name).get('val') + invoice_amount_total, 2)
                        get_hsn_data.get(hsn_status).get(hsn_name)['val'] = invoice_amount_total
                    else:
                        invoice_amount_total = round(invoice_amount_total, 2)
                        get_hsn_data.get(hsn_status).get(hsn_name)['val'] = invoice_amount_total
                    if get_hsn_data.get(hsn_status).get(hsn_name).get('tax_value'):
                        invoice_line_untaxed_amt = round(
                            get_hsn_data.get(hsn_status).get(hsn_name).get('tax_value') + invoice_line_untaxed_amt, 2)
                        get_hsn_data.get(hsn_status).get(hsn_name)['tax_value'] = invoice_line_untaxed_amt
                    else:
                        invoice_line_untaxed_amt = round(invoice_line_untaxed_amt, 2)
                        get_hsn_data.get(hsn_status).get(hsn_name)['tax_value'] = invoice_line_untaxed_amt
                    if get_hsn_data.get(hsn_status).get(hsn_name).get('gst_round_amt'):
                        igst = round(get_hsn_data.get(hsn_status).get(hsn_name).get('gst_round_amt') + igst, 2)
                        get_hsn_data.get(hsn_status).get(hsn_name)['gst_round_amt'] = igst
                    else:
                        igst = round(igst, 2)
                        get_hsn_data.get(hsn_status).get(hsn_name)['gst_round_amt'] = igst
                    if get_hsn_data.get(hsn_status).get(hsn_name).get('cgst_amt'):
                        cgst = round(get_hsn_data.get(hsn_status).get(hsn_name).get('cgst_amt') + cgst, 2)
                        get_hsn_data.get(hsn_status).get(hsn_name)['cgst_amt'] = cgst
                    else:
                        cgst = round(cgst, 2)
                        get_hsn_data.get(hsn_status).get(hsn_name)['cgst_amt'] = cgst
                    if get_hsn_data.get(hsn_status).get(hsn_name).get('sgst_amt'):
                        sgst = round(hsn_get.get(hsn_status).get(hsn_name).get('sgst_amt') + sgst, 2)
                        hsn_get.get(hsn_status).get(hsn_name)['sgst_amt'] = sgst
                    else:
                        sgst = round(sgst, 2)
                        hsn_get.get(hsn_status).get(hsn_name)['sgst_amt'] = sgst
                else:
                    count = count + 1
                    hsn_get.get(hsn_status)[hsn_name] = {
                        'num': count,
                        'hsn_sc': hsn_status,
                        'desc': hsn_name,
                        'unit_code': unit_code,
                        'qty': invoice_qty,
                        'val': invoice_amount_total,
                        'tax_value': invoice_line_untaxed_amt,
                        'gst_round_amt': igst,
                        'cgst_amt': cgst,
                        'sgst_amt': sgst,
                        'cess_amt': 0.0
                    }
            else:
                count = count + 1
                hsn_get[hsn_status] = {
                    hsn_name: {
                        'num': count,
                        'hsn_sc': hsn_status,
                        'desc': hsn_name,
                        'unit_code': unit_code,
                        'qty': invoice_qty,
                        'val': invoice_amount_total,
                        'tax_value': invoice_line_untaxed_amt,
                        'gst_round_amt': igst,
                        'cgst_amt': cgst,
                        'sgst_amt': sgst,
                        'cess_amt': 0.0
                    }
                }
            hsn_product_data = False
            if obj_product.l10n_in_hsn_code:
                hsn_product_data = obj_product.l10n_in_hsn_code.replace('.', '')
            hsnData = [
                hsn_product_data, obj_product.name, unit_code, invoice_qty,
                invoice_amount_total, invoice_line_untaxed_amt, igst, cgst, sgst, 0.0
            ]
            if get_hsn_data.get(hsn_status):
                get_hsn_data.get(hsn_status)[hsn_name] = hsnData
            else:
                get_hsn_data[hsn_status] = {hsn_name: hsnData}
            import_data.append(hsnData)
        return [import_data, json_data, get_hsn_data, hsn_get]
