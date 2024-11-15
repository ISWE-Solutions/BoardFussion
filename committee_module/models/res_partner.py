
from odoo import models, fields, api
from odoo.exceptions import RedirectWarning
from odoo.exceptions import ValidationError, UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # def toggle_active(self):
    #     super().toggle_active()  # Call the parent method
    #
    #     for partner in self:
    #         if not partner.active:
    #             print(f"Archiving partner: {partner.name} (ID: {partner.id})")
    #
    #             # Archive associated user, if active
    #             user = self.env['res.users'].search([('partner_id', '=', partner.id), ('active', '=', True)])
    #             if user:
    #                 print(f"Archiving associated user: {user.login}")
    #                 user.write({'active': False})  # Deactivate user
    #
    #             # Archive related users through employee_ids if they are active
    #             related_users = self.env['res.users'].search([
    #                 ('employee_ids', 'in', partner.id),
    #                 ('active', '=', True)  # Only consider active users for archiving
    #             ])
    #             if related_users:
    #                 print(f"Found active users related to partner {partner.name}: {[u.login for u in related_users]}")
    #                 related_users.write({'active': False})  # Deactivate related users
    #                 print(f"Archived {len(related_users)} user(s) related to partner {partner.name}")
    #             else:
    #                 print(f"No active users found related to partner {partner.name}")
    #
    #         else:
    #             print(f"Activating partner: {partner.name} (ID: {partner.id})")
    #
    #             # Unarchive associated user, if archived
    #             user = self.env['res.users'].search([('partner_id', '=', partner.id), ('active', '=', False)])
    #             if user:
    #                 print(f"Unarchiving associated user: {user.login}")
    #                 user.write({'active': True})  # Reactivate user
    #
    #             # Unarchive related users through employee_ids if they are archived
    #             related_users = self.env['res.users'].search([
    #                 ('employee_ids', 'in', partner.id),
    #                 ('active', '=', False)  # Only consider archived users for unarchiving
    #             ])
    #             if related_users:
    #                 print(f"Found archived users related to partner {partner.name}: {[u.login for u in related_users]}")
    #                 related_users.write({'active': True})  # Reactivate related users
    #                 print(f"Unarchived {len(related_users)} user(s) related to partner {partner.name}")
    #             else:
    #                 print(f"No archived users found related to partner {partner.name} for unarchiving.")




