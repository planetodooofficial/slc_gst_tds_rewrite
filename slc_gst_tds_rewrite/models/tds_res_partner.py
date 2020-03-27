# -*- coding: utf-8 -*-
from odoo import fields, models, _, api


class ResPartnerTDS(models.Model):
    _inherit = 'res.partner'

    check_threshold = fields.Boolean(string='Apply TDS if threshold is crossed', default=True)
    partner_type = fields.Selection([('B2B', 'B2B'), ('B2BUR', 'B2BUR'), ('IMPORT', 'IMPS/IMPG')],
                                    string='Partner Type', copy=False,
                                    compute='_compute_partner_type',
                                    help="""
                                            * B2B : B2B Supplies.
                                            * B2BUR : Inward supplies from unregistered Supplier.
                                            * IMPORT : Import of Services/Goods.
                                        """)

    @api.depends('vat')
    def _compute_partner_type(self):
        if self.country_id.code == 'IN':
            if self.vat:
                self.partner_type = 'B2B'
            else:
                self.partner_type = 'B2BUR'
        else:
            self.partner_type = 'IMPORT'

