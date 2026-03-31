from odoo import api, fields, models


class MailActivity(models.Model):
    _inherit = 'mail.activity'
    _order = 'eisenhower_quadrant_sequence asc, priority_stars desc, date_deadline asc, id desc'

    is_urgent = fields.Boolean(string='Urgent', tracking=True)
    is_important = fields.Boolean(string='Important', tracking=True)

    priority_stars = fields.Integer(
        string='Priority stars',
        default=0,
        tracking=True,
    )

    eisenhower_quadrant_sequence = fields.Integer(
        string='Quadrant position',
        default=10,
        index=True,
        tracking=True,
    )

    eisenhower_quadrant = fields.Selection(
        selection=[
            ('do', 'Do first'),
            ('schedule', 'Schedule'),
            ('delegate', 'Delegate'),
            ('eliminate', 'Eliminate / Postpone'),
        ],
        string='Eisenhower quadrant',
        compute='_compute_eisenhower_quadrant',
        store=True,
        readonly=False,
        inverse='_inverse_eisenhower_quadrant',
        tracking=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        compute='_compute_employee_id',
        store=True,
        index=True,
    )

    res_name_display = fields.Char(
        string='Related record',
        compute='_compute_res_name_display',
        store=False,
    )

    activity_age_days = fields.Integer(
        string='Activity age (days)',
        compute='_compute_activity_age_days',
        store=False,
    )

    @api.depends('user_id')
    def _compute_employee_id(self):
        employee_model = self.env['hr.employee'].sudo()
        for activity in self:
            employee = employee_model.search([
                ('user_id', '=', activity.user_id.id)
            ], limit=1) if activity.user_id else employee_model.browse()
            activity.employee_id = employee.id

    @api.depends('res_model', 'res_id')
    def _compute_res_name_display(self):
        for activity in self:
            name = False
            if activity.res_model and activity.res_id:
                try:
                    record = self.env[activity.res_model].browse(activity.res_id)
                    if record.exists():
                        name = record.display_name
                except Exception:
                    name = False
            activity.res_name_display = name or '/'

    @api.depends('date_deadline')
    def _compute_activity_age_days(self):
        today = fields.Date.context_today(self)
        for activity in self:
            if activity.date_deadline:
                activity.activity_age_days = (today - activity.date_deadline).days
            else:
                activity.activity_age_days = 0

    @api.depends('is_urgent', 'is_important')
    def _compute_eisenhower_quadrant(self):
        mapping = {
            (True, True): 'do',
            (False, True): 'schedule',
            (True, False): 'delegate',
            (False, False): 'eliminate',
        }
        for activity in self:
            activity.eisenhower_quadrant = mapping[(bool(activity.is_urgent), bool(activity.is_important))]


    def _inverse_eisenhower_quadrant(self):
        quadrant_map = self._quadrant_map()
        for activity in self:
            values = quadrant_map.get(activity.eisenhower_quadrant, {})
            activity.is_urgent = values.get('is_urgent', False)
            activity.is_important = values.get('is_important', False)

    @api.model
    def _quadrant_map(self):
        return {
            'do': {'is_urgent': True, 'is_important': True},
            'schedule': {'is_urgent': False, 'is_important': True},
            'delegate': {'is_urgent': True, 'is_important': False},
            'eliminate': {'is_urgent': False, 'is_important': False},
        }

    @api.model
    def _get_last_quadrant_sequence(self, quadrant):
        activity = self.search(
            [('eisenhower_quadrant', '=', quadrant)],
            order='eisenhower_quadrant_sequence desc, id desc',
            limit=1,
        )
        return activity.eisenhower_quadrant_sequence if activity else 0

    def _normalize_quadrant_sequences(self, quadrant):
        quadrant_records = self.search(
            [('eisenhower_quadrant', '=', quadrant)],
            order='eisenhower_quadrant_sequence asc, priority_stars desc, date_deadline asc, id desc',
        )
        sequence = 10
        for record in quadrant_records:
            if record.eisenhower_quadrant_sequence != sequence:
                record.with_context(mail_notrack=True).write({
                    'eisenhower_quadrant_sequence': sequence
                })
            sequence += 10

    def write(self, vals):
        if 'priority_stars' in vals:
            vals['priority_stars'] = max(0, min(3, int(vals['priority_stars'] or 0)))

        original_quadrants = {record.id: record.eisenhower_quadrant for record in self}

        if 'eisenhower_quadrant' in vals and ('is_urgent' not in vals or 'is_important' not in vals):
            vals.update(self._quadrant_map().get(vals['eisenhower_quadrant'], {}))

        if 'eisenhower_quadrant' in vals and 'eisenhower_quadrant_sequence' not in vals:
            vals['eisenhower_quadrant_sequence'] = self._get_last_quadrant_sequence(vals['eisenhower_quadrant']) + 10

        result = super().write(vals)

        quadrants_to_normalize = set()
        for record in self:
            old_quadrant = original_quadrants.get(record.id)
            if old_quadrant and old_quadrant != record.eisenhower_quadrant:
                quadrants_to_normalize.add(old_quadrant)
                quadrants_to_normalize.add(record.eisenhower_quadrant)

        for quadrant in quadrants_to_normalize:
            self._normalize_quadrant_sequences(quadrant)

        return result

    @api.model_create_multi
    def create(self, vals_list):
        quadrant_map = self._quadrant_map()

        for vals in vals_list:
            quadrant = vals.get('eisenhower_quadrant')

            if quadrant and ('is_urgent' not in vals or 'is_important' not in vals):
                vals.update(quadrant_map.get(quadrant, {}))

            vals['priority_stars'] = max(0, min(3, int(vals.get('priority_stars', 0) or 0)))

            if quadrant and not vals.get('eisenhower_quadrant_sequence'):
                vals['eisenhower_quadrant_sequence'] = self._get_last_quadrant_sequence(quadrant) + 10

        return super().create(vals_list)

    def action_open_related_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': self.res_name_display or 'Related record',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_set_priority_stars(self, stars):
        self.ensure_one()
        stars = max(0, min(3, int(stars or 0)))
        self.write({'priority_stars': stars})
        return True

    def action_move_up_in_quadrant(self):
        self.ensure_one()

        previous_record = self.search(
            [
                ('eisenhower_quadrant', '=', self.eisenhower_quadrant),
                ('eisenhower_quadrant_sequence', '<', self.eisenhower_quadrant_sequence),
            ],
            order='eisenhower_quadrant_sequence desc, priority_stars asc, date_deadline desc, id asc',
            limit=1,
        )

        if not previous_record:
            return True

        current_sequence = self.eisenhower_quadrant_sequence
        previous_sequence = previous_record.eisenhower_quadrant_sequence

        self.with_context(mail_notrack=True).write({
            'eisenhower_quadrant_sequence': previous_sequence
        })
        previous_record.with_context(mail_notrack=True).write({
            'eisenhower_quadrant_sequence': current_sequence
        })
        return True

    def action_move_down_in_quadrant(self):
        self.ensure_one()

        next_record = self.search(
            [
                ('eisenhower_quadrant', '=', self.eisenhower_quadrant),
                ('eisenhower_quadrant_sequence', '>', self.eisenhower_quadrant_sequence),
            ],
            order='eisenhower_quadrant_sequence asc, priority_stars desc, date_deadline asc, id desc',
            limit=1,
        )

        if not next_record:
            return True

        current_sequence = self.eisenhower_quadrant_sequence
        next_sequence = next_record.eisenhower_quadrant_sequence

        self.with_context(mail_notrack=True).write({
            'eisenhower_quadrant_sequence': next_sequence
        })
        next_record.with_context(mail_notrack=True).write({
            'eisenhower_quadrant_sequence': current_sequence
        })
        return True