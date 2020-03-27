{
  "name"                 :  "GST and TDS",
  "summary"              :  "1.Tax Deducted at Source."
                            "2.GST Reports",
  "category"             :  "Account",
  "version"              :  "13.0.0",
  "sequence"             :  1,
  "author"               :  "Planet Odoo",
  "company"              :  "Planet Odoo",
  "website"              :  "http://www.planet-odoo.com/",
  "description"          :  """This Module will help you to:
                               1.Apply TDS or withholding tax at the time of invoice or payment.
                               2.Generate csv. Some of the features include:Export B2B csv, Export B2Cl csv. Export B2CS csv, Export HSN csv.""",
  "depends"              :  [
                             'account', 'l10n_in', 'account_tax_python', 'base'
                            ],
  "data"                 :  [
                                'data/gst_quantity_code.xml',
                                'data/gst_unit_mapping.xml',
                                'data/gst_dashboard_view.xml',
                                'security/gst_user_access.xml',
                                'security/ir.model.access.csv',
                                'wizard/wizard_invoice_type_view.xml',
                                'wizard/gst_message_view.xml',
                                'data/gst_invoice_server_update.xml',
                                'views/tds_account_view.xml',
                                'views/account_move_view.xml',
                                'views/account_payment_tds_view.xml',
                                'views/gst_tool_view.xml',
                                'views/gstr_tool_view.xml',
                                'views/tds_res_partner_view.xml',
                                'views/gst_assets.xml',
                                'views/gst_dashboard_view.xml',
                                'views/gst_fiscal_view.xml',
                                'views/gst_attachments.xml',
                                'views/gst_account_period_view.xml',
                                'views/gst_sequence.xml',
                                'views/gst_quantity_code.xml',
                                'views/gst_unit_mapping_view.xml',
                                'views/gst_action_view.xml',
                                'views/gst_menu_view.xml',

  ],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "EUR",
}
