# -*- coding: utf-8 -*-
from odoo import fields, models, _


class AccountTDS(models.Model):
    _inherit = 'account.tax'

    apply_tds = fields.Boolean('Apply TDS', default=False)
    excess_of = fields.Float('In excess of')
    apply_tds_to = fields.Selection([('individual', 'Individual'),
                                     ('company', 'Company'),
                                     ('both', 'Both')], string='Apply TDS to')
