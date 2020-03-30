# -*- coding: utf-8 -*-
from odoo import api, models


class WizardDataCSV(models.TransientModel):
    _name = "data.csv.wizard"

    def HSN_data_create(self):
        data_cols = [
            'HSN',
            'Description',
            'Unit Code',
            'Total Quantity',
            'Total Value',
            'Taxable Amount'
            'Integrated Tax Amount',
            'Central Tax Amount',
            'State/UT Tax Amount',
            'Cess Amount'
        ]
        return data_cols

    def b2bur_data_create(self):
        data_cols = [
            'Supplier Name',
            'Invoice Number',
            'Date of Invoice',
            'Invoice Value',
            'Place Of Supply',
            'Supply Type',
            'Rate',
            'Taxable Amount'
            'Integrated Tax Paid',
            'Central Tax Paid',
            'State/UT Tax Paid',
            'Cess Amount',
            'Eligibility For ITC',
            'Availed ITC Integrated Tax',
            'Availed ITC Central Tax',
            'Availed ITC State/UT Tax',
            'Availed ITC Cess'
        ]
        return data_cols

    def b2b_data_create(self, gst_return_type):
        data_cols = []
        if gst_return_type == 'gstr1':
            data_cols = [
                'GSTIN/UIN',
                'Receiver Name',
                'Invoice Number',
                'Date of Invoice',
                'Invoice Value',
                'Place Of Supply',
                'Reverse Charge',
                'Applicable % of Tax Rate',
                'Invoice Type',
                'E-Commerce GSTIN',
                'Rate',
                'Taxable Amount'
                'Cess Amount'
            ]
        if gst_return_type == 'gstr2':
            data_cols = [
                'GSTIN',
                'Invoice Number',
                'Date of Invoice',
                'Invoice Value',
                'Place Of Supply',
                'Reverse Charge',
                'Invoice Type',
                'Rate',
                'Taxable Amount'
                'Integrated Tax Paid',
                'Central Tax Paid',
                'State/UT Tax Paid',
                'Cess Amount',
                'Eligibility For ITC',
                'Availed ITC Integrated Tax',
                'Availed ITC Central Tax',
                'Availed ITC State/UT Tax',
                'Availed ITC Cess'
            ]

        return data_cols

    def b2cl_data_create(self):
        data_cols = [
            'Invoice Number',
            'Date of Invoice',
            'Invoice Value',
            'Place Of Supply',
            'Applicable % of Tax Rate',
            'Rate',
            'Taxable Amount'
            'Cess Amount',
            'E-Commerce GSTIN',
            'Sale from Bonded WH'
        ]
        return data_cols

    def b2cs_data_create(self):
        data_cols = [
            'Type',
            'Place Of Supply',
            'Applicable % of Tax Rate',
            'Rate',
            'Taxable Amount'
            'Cess Amount',
            'E-Commerce GSTIN'
        ]
        return data_cols

    def import_imps_data_create(self):
        data_cols = [
            'Invoice Number of Reg Recipient',
            'Date of Invoice',
            'Invoice Value',
            'Place Of Supply',
            'Rate',
            'Taxable Amount'
            'Integrated Tax Paid',
            'Cess Amount',
            'Eligibility For ITC',
            'Availed ITC Integrated Tax',
            'Availed ITC Cess'
        ]
        return data_cols

    def import_impg_data_create(self):
        data_cols = [
            'Port Code',
            'Bill Of Entry Number',
            'Bill Of Entry Date',
            'Bill Of Entry Value',
            'Document type',
            'GSTIN Of SEZ Supplier',
            'Rate',
            'Taxable Amount'
            'Integrated Tax Paid',
            'Cess Amount',
            'Eligibility For ITC',
            'Availed ITC Integrated Tax',
            'Availed ITC Cess'
        ]
        return data_cols

    def export_data_create(self):
        data_cols = [
            'Export Type',
            'Invoice Number',
            'Date of Invoice',
            'Invoice Value',
            'Port Code',
            'Shipping Bill Number',
            'Shipping Bill Date',
            'Applicable % of Tax Rate',
            'Rate',
            'Taxable Value'
        ]
        return data_cols

