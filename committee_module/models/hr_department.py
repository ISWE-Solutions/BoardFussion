from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Department(models.Model):
    _name = "hr.department"
    _description = "Committee"
    _inherit = ["hr.department", "documents.mixin"]

    workspace_id = fields.Many2one("documents.folder", string="Workspace")
    document_count = fields.Integer(compute="_compute_document_count")

    def _compute_total_employee(self):
        result = {}
        count_total_employee = 0
        emp_data = self.env['hr.employee'].search([])

        for department in self.ids:
            for employee in emp_data:
                for committee in employee.committees_ids:
                    if committee.id == department:
                        count_total_employee += 1
            result[department] = count_total_employee
            count_total_employee = 0
        for department in self:
            department.total_employee = result.get(department.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if "name" in val:
                workspace = val["name"]
                workspace_env = self.env["documents.folder"].sudo().create({"name": workspace})
                val["workspace_id"] = workspace_env.id
        return super().create(vals_list)

    def _compute_document_count(self):
        # Method not optimized for batches since it is only used in the form view.
        for committee in self:

            if committee:
                domain = [
                    "|",
                    ("committee_id", "=", committee.id),
                    ("folder_id", "=", committee.workspace_id.id),
                    ("owner_id", "=", self.create_uid.id),
                ]
                committee.document_count = self.env["documents.document"].search_count(domain)
            else:
                committee.document_count = 0

    def _get_committie_document_domain(self):
        self.ensure_one()
        user_domain = [("committee_id", "=", self.id)]
        if self.create_uid:
            user_domain = expression.OR([user_domain, [("owner_id", "=", self.create_uid.id)]])
        return user_domain

    def action_open_documents(self):
        self.ensure_one()
        hr_folder = self.workspace_id
        action = self.env["ir.actions.act_window"]._for_xml_id("documents.document_action")
        action["context"] = {
            "default_committee_id": self.id,
            "searchpanel_default_folder_id": hr_folder and hr_folder.id,
        }
        action["domain"] = self._get_committie_document_domain()
        return action
