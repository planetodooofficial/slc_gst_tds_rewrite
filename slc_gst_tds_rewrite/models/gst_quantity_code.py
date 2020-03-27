from odoo import api, fields, models


class UnitQuantityCode(models.Model):
    _name = "unit.quantity.code"
    _description = "Unit Quantity Code"

    name = fields.Char(string="Unit", help="UQC (Unit of Measure) of goods sold")
    code = fields.Char(string="Code", help="Code for UQC (Unit of Measure)")