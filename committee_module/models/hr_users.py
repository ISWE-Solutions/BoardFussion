from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)
class User(models.Model):
    _inherit = 'res.users'

    member_type = fields.Selection(related='employee_id.member_type', string='Member Type', readonly=False, store=True)

    def write(self, vals):
        res = super(User, self).write(vals)

        # Fields to propagate
        fields_to_sync = ['name', 'phone', 'mobile', 'work_email', 'job_description']
        for user in self:
            for field in fields_to_sync:
                if field in vals:
                    # Update related employee
                    employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                    if employee:
                        employee.write({field: vals[field]})

                    # Update related partner
                    if user.partner_id:
                        user.partner_id.write({field: vals[field]})

        return res

    def toggle_active(self):
        super().toggle_active()  # Call the parent method

        for user in self:
            if not user.active:  # User is being archived
                print(f"Archiving user: {user.login} (ID: {user.id})")

                # Check if there is an associated employee record
                employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)

                if not employee:  # Only proceed if no associated employee
                    # Archive related partners
                    partners_to_archive = self.env['res.partner'].search([
                        '|',  # Use OR to search for both conditions
                        ('employee_ids.user_id', '=', user.id),  # Partners related via employee_ids
                        ('id', '=', user.partner_id.id),  # Partners linked via partner_id
                        ('active', '=', True)  # Only consider active partners for archiving
                    ])

                    if partners_to_archive:
                        print(
                            f"Found active partners related to user {user.login}: {[partner.name for partner in partners_to_archive]}")
                        partners_to_archive.write({'active': False})  # Deactivate partners
                        print(f"Archived {len(partners_to_archive)} partner(s) related to user {user.login}")
                    else:
                        print(f"No active partners found related to user {user.login}.")
                else:
                    print(f"User {user.login} has an associated employee. Skipping partner archiving.")

    def unlink(self):
        for user in self:
            # Check if there is an associated employee record
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)

            if employee:  # User has an associated employee
                print(f"User {user.login} has an associated employee. Archiving user only.")
                user.active = False  # Archive the user

            else:  # No associated employee
                print(f"User {user.login} has no associated employee. Deleting user and archiving partners.")

                # Archive the user first
                user.active = False  # Archive the user

                # Archive related partners
                partners_to_archive = self.env['res.partner'].search([
                    '|',  # Use OR to search for both conditions
                    ('employee_ids.user_id', '=', user.id),  # Partners related via employee_ids
                    ('id', '=', user.partner_id.id),  # Partners linked via partner_id
                    ('active', '=', True)  # Only consider active partners for archiving
                ])

                if partners_to_archive:
                    partners_to_archive.write({'active': False})  # Deactivate partners
                    print(f"Archived {len(partners_to_archive)} partner(s) related to user {user.login}")
                else:
                    print(f"No active partners found related to user {user.login}.")

        # Note: Do not call super().unlink() since we are archiving instead of deleting

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            email = vals.get("login")
            if email:
                # Normalize the email: remove extra spaces and convert to lowercase.
                normalized_email = email.strip().lower()
                _logger.info(
                    "Processing user creation with email: '%s' normalized to '%s'",
                    email, normalized_email
                )

                # Search for existing partner records with an email matching normalized_email.
                # Using 'ilike' makes the search case-insensitive.
                search_domain = [("email", "ilike", normalized_email)]
                partners_found = self.env["res.partner"].search(search_domain)
                _logger.info("Search domain: %s, found %s partner(s)", search_domain, len(partners_found))

                partner = None
                # Iterate over found partners to see if one matches exactly when normalized.
                for p in partners_found:
                    if p.email and p.email.strip().lower() == normalized_email:
                        partner = p
                        _logger.info(
                            "Exact match found: Partner ID %s with email '%s'",
                            p.id, p.email
                        )
                        break

                if partner:
                    _logger.info("Using existing partner: ID %s", partner.id)
                    vals["partner_id"] = partner.id
                else:
                    _logger.info("No exact partner found for email '%s'. Creating new partner.", normalized_email)
                    partner = self.env["res.partner"].create({
                        "name": vals.get("name", normalized_email),
                        "email": normalized_email,
                    })
                    _logger.info("Created new partner: ID %s with email '%s'", partner.id, partner.email)
                    vals["partner_id"] = partner.id
            else:
                _logger.warning("User creation skipped: No email provided in values: %s", vals)

        # Create the user(s) using the super method.
        users = super(User, self).create(vals_list)

        # Additional post-processing and logging.
        for user in users:
            if user.partner_id.company_id:
                user.partner_id.company_id = user.company_id
                _logger.info(
                    "Assigned company %s to partner %s",
                    user.company_id.id, user.partner_id.id
                )

            user.partner_id.active = user.active
            _logger.info(
                "Set partner active status for user %s (partner %s) to %s",
                user.id, user.partner_id.id, user.active
            )

            if not user.image_1920 and not user.share and user.name:
                avatar_svg = user.partner_id._avatar_generate_svg()
                user.image_1920 = avatar_svg
                _logger.info("Generated avatar for user %s", user.id)

            _logger.info("Final user created: %s with partner %s", user, user.partner_id)

        return users