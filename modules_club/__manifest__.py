{
  "name"                 :  "SLC modules",
  "summary"              :  "1.Tax Deducted at Source(TDS) or Withholding Tax."
                            "2.Supplier Advance Payment"
                            "3.Odoo Dynamic Bank Cheque Print"
                            "4.GST Invoice Reports",
  "category"             :  "Account",
  "version"              :  "13.0.0",
  "sequence"             :  1,
  "author"               :  "Planet Odoo",
  "company"              :  "Planet Odoo",
  "website"              :  "http://www.planet-odoo.com/",
  "description"          :  """This Module will help you to:
                               1.Apply TDS or withholding tax at the time of invoice or payment.
                               2.Make an advance payment on Purchase Orders. In some cases, vendor may need to pay advance payment.
                               3.Set various attributes of bank cheque dynamically, so you can print bank cheque in a easy manner.
                               4.Generate csv. Some of the features include:Export B2B csv, Export B2Cl csv. Export B2CS csv, Export HSN csv.""",
  "depends"              :  [
                             'account', 'website', 'l10n_in', 'account_tax_python', 'web', 'base', 'purchase'
                            ],
  "data"                 :  [
                            'data/data_unit_quantity_code.xml',
                            'data/data_uom_mapping.xml',
                            'data/data_dashboard.xml',
                            'security/gst_security.xml',
                            'security/ir.model.access.csv',
                            'data/cheque_attribute_data.xml',
                            'wizard/message_wizard_view.xml',
                            'wizard/invoice_type_wizard_view.xml',
                            'data/gob_server_actions.xml',
                            'views/account_move_view.xml',
                            'views/gst_view.xml',
                            'views/gstr2_view.xml',
                            'views/res_partner_views.xml',
                            'views/gst_templates.xml',
                            'views/gst_dashboard_view.xml',
                            'views/account_fiscalyear_view.xml',
                            'views/ir_attachment_view.xml',
                            'views/account_period_view.xml',
                            'views/gst_sequence.xml',
                            'views/unit_quantity_code_view.xml',
                            'views/uom_map_view.xml',
                            'views/gst_action_view.xml',
                            'views/gst_menu_view.xml',
                            'wizard/invoice_print_cheque_transient_views.xml',
                            'views/account_invoice_inherit_view.xml',
                            'views/bank_cheque_views.xml',
                            'views/website_template_view.xml',
                            'views/cheque_report.xml',
                            'views/account_view.xml',
                            'views/res_partner_view.xml',
                            'views/account_payment_view.xml',
                            'views/account_invoice_view.xml',
                            'views/purchase_order.xml',
                            'views/account_payment.xml',
                            'views/account_move.xml',
                            ],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "EUR",
  "pre_init_hook"        :  "pre_init_check",
}
