# -*- coding: utf-8 -*-
from odoo import api, models


class WizardTaxGST(models.TransientModel):
    _name = "wizard.tax.gst"

    def gst_tax_data(self, gst_invoice_obj, obj_invoice_line, obj_rate, amount_taxed, invoice_type):
        amount_taxed = round(amount_taxed, 2)
        gst_data = {
            "gst_amt": 0.0,
            "gst_round_amt": 0.0,
            "cgst_amt": 0.0,
            "sgst_amt": 0.0,
            "cess_amt": 0.0
        }
        if invoice_type == "export":
            gst_data = {"tax_value": 0.0, "gst_amt": 0, "gst_round_amt": 0.0}
        if invoice_type in ['imps', 'impg']:
            gst_data = {
                "itc_eligibility": "no",
                "tax_value": 0.0,
                "gst_amt": 0,
                "gst_round_amt": 0.0,
                'tax_invoice': 0.0,
                'tax_cess': 0.0
            }
        if invoice_type == "b2cs":
            gst_data['supply_state'] = 'INTRA'
            gst_data['typ'] = 'OE'
        if obj_rate:
            if gst_invoice_obj.partner_id.country_id.code == 'IN':
                for rate_obj in obj_rate:
                    if rate_obj.amount_type == "group":
                        for childObj in rate_obj.children_tax_ids:
                            gst_data['gst_amt'] = childObj.amount * 2
                            gst_data['sgst_amt'] = round(amount_taxed / 2, 2)
                            gst_data['cgst_amt'] = round(amount_taxed / 2, 2)
                            break
                    else:
                        gst_data['gst_amt'] = rate_obj.amount
                        gst_data['gst_round_amt'] = round(amount_taxed, 2)
                    break
            elif invoice_type in ['imps', 'impg']:
                for rate_obj in obj_rate:
                    gst_data['gst_amt'] = rate_obj.amount
                    gst_data['gst_round_amt'] = round(amount_taxed, 2)
                    break
        return gst_data

    def compute_taxed_amount(self, obj_rate, price, currency, obj_invoice_line, gst_invoice_objs):
        amount_taxed = 0.0
        total_excluded = 0.0
        compute_tax = obj_rate.compute_all(price, currency, obj_invoice_line.quantity,
                                     product=obj_invoice_line.product_id, partner=gst_invoice_objs.partner_id)
        if compute_tax:
            total_included = compute_tax.get('total_included') or 0.0
            total_excluded = compute_tax.get('total_excluded') or 0.0
            amount_taxed = total_included - total_excluded
        if currency.name != 'INR':
            amount_taxed = amount_taxed * currency.rate
            total_excluded = total_excluded * currency.rate
        return [amount_taxed, total_excluded]


