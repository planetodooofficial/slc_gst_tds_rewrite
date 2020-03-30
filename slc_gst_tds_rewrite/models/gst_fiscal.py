# -*- coding: utf-8 -*-
import time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError
from odoo.osv import expression


class AccountFiscalYear(models.Model):
    _name = "account.fiscal_year"
    _order = "start_period, id"

    name = fields.Char('Fiscal Year', required=True)
    code = fields.Char('Reference Number', size=6, required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.move'))
    start_period = fields.Date('Start of Fiscal Period', required=True,
                               default=lambda *a: time.strftime('%Y-%m-01 %H:59:%S'))
    end_period = fields.Date('End of Fiscal Period', required=True,
                             default=lambda *a: time.strftime('%Y-12-31 %H:59:%S'))
    fy_ids = fields.One2many('account.period', 'fiscal_year_id', 'Fiscal Year Periods')

    @api.constrains('start_period', 'end_period')
    def check_start_end_periods(self):
        if self.end_period < self.start_period:
            raise UserError(_('End period is before start period'))

    def create_period(self, interval=1):
        fiscal_period_obj = self.env['account.period']
        for period in self:
            start_period = period.start_period
            fiscal_period_obj.create({
                'name': "%s %s" % (_('Opening Fiscal Period'), start_period.strftime('%Y')),
                'code': start_period.strftime('00/%Y'),
                'start_period': start_period,
                'end_period': start_period,
                'open_close_period': True,
                'fiscal_year_id': period.id,
            })
            while start_period < period.end_period:
                date_end = start_period + relativedelta(months=interval, days=-1)
                if date_end > period.end_period:
                    date_end = period.end_period
                fiscal_period_obj.create({
                    'name': start_period.strftime('%b-%Y'),
                    'code': start_period.strftime('%m/%Y'),
                    'start_period': start_period,
                    'end_period': date_end,
                    'fiscal_year_id': period.id,
                })
                start_period = start_period + relativedelta(months=interval)
        return True

    def create_quarterly_period(self):
        return self.create_period(3)

    def create_monthly_period(self):
        return self.create_period(1)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        name_search_obj = self.search(expression.AND([domain, args]), limit=limit)
        return name_search_obj.name_get()

    @api.model
    def find(self, today_date=None, exception=True):
        context = self._context
        if context is None:
            context = {}
        if not today_date:
            today_date = fields.date.context_today(self)
        start_end_check = [('start_period', '<=', today_date), ('end_period', '>=', today_date)]
        if context.get('company_id', False):
            company_id = context['company_id']
        else:
            company_id = self.env['res.users'].browse(self._uid).company_id.id
        start_end_check.append(('company_id', '=', company_id))
        start_end_obj = self.search(start_end_check)
        if not start_end_obj:
            if exception:
                model, go_to_id = self.env['ir.model.data'].get_object_reference('account',
                                                                                 'gst_account_fiscal_year_action')
                raise RedirectWarning(_('Please go to Configuration panel since there is no period defined for: %s')
                                      % today_date, go_to_id)
            else:
                return []
        start_end_ids = start_end_obj.ids
        return start_end_ids and start_end_ids[0] or False
