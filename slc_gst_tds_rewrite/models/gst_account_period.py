from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError, RedirectWarning


class AccountPeriodGST(models.Model):
    _name = "account.period"
    _order = "start_period, open_close_period desc"

    name = fields.Char('Fiscal Period Name', required=True)
    code = fields.Char('Reference Number')
    open_close_period = fields.Boolean('Opening/Closing of Fiscal Period', compute='compute_open_close_period')
    start_period = fields.Date('Start of Fiscal Period', required=True)
    end_period = fields.Date('End of Fiscal Period', required=True)
    fiscal_year_id = fields.Many2one('account.fiscal_year', 'Fiscal Year', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 related='fiscal_year_id.company_id', store=True, readonly=True)

    _sql_constraints = [('unique_company_name', 'unique(name, company_id)',
                         'The period name should be unique for each company!'), ]

    @api.constrains('end_period')
    def check_start_end_periods(self):
        if self.end_period < self.start_period:
            raise UserError(_('End period is before start period'))
        for start_end_check in self:
            if start_end_check.open_close_period:
                continue
            if start_end_check.fiscal_year_id.end_period < start_end_check.end_period:
                if start_end_check.fiscal_year_id.end_period < start_end_check.start_period:
                    if start_end_check.fiscal_year_id.start_period > start_end_check.start_period:
                        if start_end_check.fiscal_year_id.start_period > start_end_check.end_period:
                            return False
            start_end_obj = self.search([('id', '<>', start_end_check.id),
                                         ('start_period', '<=', start_end_check.end_period),
                                         ('end_period', '>=', start_end_check.start_period)
                                         ])
            for period in start_end_obj:
                if fields.Date.today() - timedelta(days=30) < period.end_period < fields.Date.today():
                    continue
                if period.fiscal_year_id.company_id.id == start_end_check.fiscal_year_id.company_id.id:
                    raise UserError(_('The period is either wrong or overlapping'))

    @api.returns('self')
    def find(self, today_date=None):
        context = self._context
        if context is None:
            context = {}
        if not today_date:
            today_date = fields.date.context_today(self)
        start_end_find = [('start_period', '<=', today_date), ('end_period', '>=', today_date)]
        if context.get('company_id', False):
            start_end_find.append(('company_id', '=', context['company_id']))
        else:
            company_id = self.env['res.users'].browse(self._uid).company_id.id
            start_end_find.append(('company_id', '=', company_id))
        find_period = []
        if context.get('account_period_prefer_normal', True):
            find_period = self.search(find_period + [('open_close_period', '=', False)])
        if not find_period:
            find_period = self.search(find_period)
        if not find_period:
            model, go_to_id = self.env['ir.model.data'].get_object_reference('account', 'gst_account_period_action')
            raise RedirectWarning(_('Please go to Configuration panel since there is no period defined for: %s')
                                  % today_date
                                  , go_to_id)
        return find_period

    @api.returns('self')
    def next(self, period, count_start):
        start_id_next = self.search([('start_period', '>', period.start_period)])
        if len(start_id_next) >= count_start:
            return start_id_next[count_start - 1]
        return False

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        objs = self.search(expression.AND([domain, args]), limit=limit)
        return objs.name_get()

    def write(self, vals):
        if 'company_id' in vals:
            account_move_lines = self.env['account.move.line'].search([('fy_id', 'in', self.ids)])
            if account_move_lines:
                raise UserError(_('Company Field cannot be modified since journal items already exists'))
        return super(AccountPeriodGST, self).write(vals)

    @api.model
    def compute_start_end_period(self, start_id, end_id):
        start_period = self.browse(start_id).start_period
        end_period = self.browse(end_id).end_period
        if self.browse(start_id).company_id.id != self.browse(end_id).company_id.id:
            raise UserError(_('Please choose the same company'))

        if start_period > end_period:
            raise UserError(_('End period is before start period'))

        if start_id == end_id:
            return start_id

        if self.browse(start_id).open_close_period:
            return self.search([('start_period', '>=', start_period), ('end_period', '<=', end_period)])

        return self.search([('open_close_period', '=', False), ('start_period', '>=', start_period),
                            ('end_period', '<=', end_period)])

    @api.depends('end_period')
    def compute_open_close_period(self):
        start_date = fields.Date.today() - timedelta(days=30)
        for period in self:
            if period.end_period:
                if period.end_period < start_date:
                    period.open_close_period = True
                else:
                    period.open_close_period = False
