from odoo import api, fields, models, _


class UomMapping(models.Model):
    _name = "uom.mapping"
    _description = "UOM Mapping"

    name = fields.Many2one("unit.quantity.code", string="Unit Quantity Code", help="UQC (Unit of Measure) of goods sold")
    uom = fields.Many2one("uom.uom", string="Units of Measure", help="Units of Measure use for all stock operation")
