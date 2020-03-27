from odoo import api, fields, models


class MessageWizard(models.TransientModel):
    _name = "message.wizard"
    _description = "Message wizard"

    text = fields.Text(string='Message', readonly=True, translate=True)
