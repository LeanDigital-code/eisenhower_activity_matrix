# -*- coding: utf-8 -*-

from odoo import fields, models


class MailActivityColor(models.Model):
    _inherit = 'mail.activity'

    kanban_color = fields.Integer(
        string='Kanban Color',
        default=0,
        help='Color label used in the Eisenhower kanban cards.',
    )
