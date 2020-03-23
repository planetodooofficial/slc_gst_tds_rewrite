# -*- coding: utf-8 -*-
import time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError
from odoo.osv import expression


class AccountFiscalyear(models.Model):
    _name = "account.fiscalyear"
    _description = "Fiscal Year"
    _order = "date_start, id"

    name = fields.Char('Fiscal Year', required=True)
    code = fields.Char('Code', size=6, required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get('account.move'))
    date_start = fields.Date('Start Date', required=True,
        default=lambda *a: time.strftime('%Y-%m-01 %H:59:%S'))
    date_stop = fields.Date('End Date', required=True,
        default=lambda *a: time.strftime('%Y-12-31 %H:59:%S'))
    period_ids = fields.One2many('account.period', 'fiscalyear_id', 'Periods')

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        if self.date_stop < self.date_start:
            raise UserError(_('Error!\nThe start date of a fiscal year must precede its end date.'))

    def create_period3(self):
        return self.create_period(3)

    def create_period1(self):
        return self.create_period(1)

    def create_period(self, interval=1):
        period_obj = self.env['account.period']
        for fy in self:
            date_start = fy.date_start
            period_obj.create({
                'name': "%s %s" % (_('Opening Period'), date_start.strftime('%Y')),
                'code': date_start.strftime('00/%Y'),
                'date_start': date_start,
                'date_stop': date_start,
                'special': True,
                'fiscalyear_id': fy.id,
            })
            while date_start < fy.date_stop:
                date_end = date_start + relativedelta(months=interval, days=-1)
                if date_end > fy.date_stop:
                    date_end = fy.date_stop
                period_obj.create({
                    'name': date_start.strftime('%b-%Y'),
                    'code': date_start.strftime('%m/%Y'),
                    'date_start': date_start,
                    'date_stop': date_end,
                    'fiscalyear_id': fy.id,
                })
                date_start = date_start + relativedelta(months=interval)
        return True

    @api.model
    def find(self, dt=None, exception=True):
        res = self.finds(dt, exception)
        return res and res[0] or False

    @api.model
    def finds(self, date_obj=None, exception=True):
        context = self._context
        if context is None: context = {}
        if not date_obj:
            date_obj = fields.date.context_today(self)
        args = [('date_start', '<=', date_obj), ('date_stop', '>=', date_obj)]
        if context.get('company_id', False):
            company_id = context['company_id']
        else:
            company_id = self.env['res.users'].browse(self._uid).company_id.id
        args.append(('company_id', '=', company_id))
        objs = self.search(args)
        if not objs:
            if exception:
                model, action_id = self.env['ir.model.data'].get_object_reference(
                        'account', 'action_account_fiscalyear')
                msg = _('There is no period defined for this date: %s.' \
                        '\nPlease go to Configuration/Periods and configure a fiscal year.') % date_obj
                raise RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            else:
                return []
        ids = objs.ids
        return ids

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
