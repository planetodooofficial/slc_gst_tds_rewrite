from odoo import api, fields, models


class UnitQuantityCode(models.Model):
    _name = "unit.quantity.code"
    _description = "Unit Quantity Code"

    name = fields.Char(string="Unit of Measure")
    code = fields.Char(string="Code for unit_code")
