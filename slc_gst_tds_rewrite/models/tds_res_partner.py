# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ResPartnerTDS(models.Model):
    _inherit = 'res.partner'

    check_threshold = fields.Boolean(string='Apply TDS if threshold is crossed', default=True)
