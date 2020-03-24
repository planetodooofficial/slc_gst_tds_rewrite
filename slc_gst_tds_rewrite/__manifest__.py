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
                                'views/tds_account_view.xml',
                                'views/account_payment_tds_view.xml',
                                'views/tds_res_partner_view.xml',
                            ],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "EUR",
  "pre_init_hook"        :  "pre_init_check",
}
