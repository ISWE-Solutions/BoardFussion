# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MailActivityPlanTemplate(models.Model):
    _inherit = 'mail.activity.plan.template'

    responsible_type = fields.Selection(selection_add=[
        ('coach', 'Coach'),
        ('manager', 'Manager'),
        ('member', 'Member'),  # Change 'employee' to 'member'
    ], ondelete={'coach': 'cascade', 'manager': 'cascade', 'member': 'cascade'})  # Update here as well

    @api.constrains('plan_id', 'responsible_type')
    def _check_responsible_hr(self):
        """ Ensure that hr types are used only on member model """
        for template in self.filtered(lambda tpl: tpl.plan_id.res_model != 'hr.employee'):
            if template.responsible_type in {'coach', 'manager', 'member'}:  # Update 'employee' to 'member'
                raise ValidationError(_('Those responsible types are limited to Member plans.'))  # Update message

    def _determine_responsible(self, on_demand_responsible, member):
        if self.plan_id.res_model != 'hr.employee' or self.responsible_type not in {'coach', 'manager', 'member'}:  # Change 'employee' to 'member'
            return super()._determine_responsible(on_demand_responsible, member)  # Update here as well
        error = False
        responsible = False
        if self.responsible_type == 'coach':
            if not member.coach_id:
                error = _('Coach of member %s is not set.', member.name)  # Change 'employee' to 'member'
            responsible = member.coach_id.user_id
            if member.coach_id and not responsible:
                error = _("The user of %s's coach is not set.", member.name)  # Change 'employee' to 'member'
        elif self.responsible_type == 'manager':
            if not member.parent_id:
                error = _('Manager of member %s is not set.', member.name)  # Change 'employee' to 'member'
            responsible = member.parent_id.user_id
            if member.parent_id and not responsible:
                error = _("The manager of %s should be linked to a user.", member.name)  # Change 'employee' to 'member'
        elif self.responsible_type == 'member':  # Change 'employee' to 'member'
            responsible = member.user_id
            if not responsible:
                error = _('The member %s should be linked to a user.', member.name)  # Change 'employee' to 'member'
        if error or responsible:
            return {
                'responsible': responsible,
                'error': error,
            }
