from odoo import api, fields, models, _


class MappingUnitMeasure(models.Model):
    _name = "uom.mapping"
    _description = "UOM Mapping"

    name = fields.Many2one("unit.quantity.code", string="Unit Quantity Reference Number")
    uom = fields.Many2one("uom.uom", string="Units of Measure")
