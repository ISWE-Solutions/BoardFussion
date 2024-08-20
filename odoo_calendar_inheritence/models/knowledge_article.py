from odoo import models, fields, api, _
from odoo.exceptions import UserError


class KnowledgeArticle(models.Model):
    _inherit = 'knowledge.article'

    calendar_id = fields.Many2one('calendar.event', string='Calendar Event')
    product_id = fields.Many2one('product.template', string='Product')
    body = fields.Html(string='Content', sanitize=True)
    is_minutes_of_meeting = fields.Boolean(default=False)

    def action_open_documents(self):
        # self.ensure_one()
        current_time = fields.Datetime.now()
        meeting_end_time = self.calendar_id.stop
        active_user = self.env.user.partner_id.id
        company_id = self.env.company.id
        domain = [
            '|',
            '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.id),
            '&',
            ('res_model', '=', 'product.template'),
            ('res_id', 'in', self.product_id.product_variant_ids.ids),
            ('partner_ids', 'in', [active_user]),]
        # if current_time and meeting_end_time:
        #     if current_time >= meeting_end_time: #If Meeting Has Ended
        #         domain = [
        #             '|',
        #             '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.id),
        #             '&',
        #             ('res_model', '=', 'product.template'),
        #             ('res_id', 'in', self.product_id.product_variant_ids.ids),
        #         ]
        #     else: #If meeting is still going!
        #         domain = [
        #             '|',
        #             '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.id),
        #             '&',
        #             ('res_model', '=', 'product.template'),
        #             ('res_id', 'in', self.product_id.product_variant_ids.ids),
        #             ('partner_ids', 'in', [active_user]),
        #         ]
        for rec in self:
            return {
                'name': _('Documents'),
                'type': 'ir.actions.act_window',
                'res_model': 'product.document',
                'view_mode': 'kanban,tree,form',
                'context': {
                    'default_res_model': rec.product_id._name,
                    'default_res_id': rec.product_id.id,
                    'default_company_id': company_id,
                },
                'domain': domain,
                'target': 'current',
                'help': """
                    <p class="o_view_nocontent_smiling_face">
                        %s
                    </p>
                    <p>
                        %s
                        <br/>
                    </p>
                """ % (
                    _("Upload Pdfs to your agenda"),
                    _("Use this feature to store pdfs you would like to share with your members"),
                )
            }

    # @api.model
    # def create_article_with_attachments(self, name, attachment_ids):
    #     if not attachment_ids:
    #         raise UserError("No attachments provided.")
    #
    #     # Create a new Knowledge article
    #     article = self.create({'name': name})
    #
    #     # Attach documents to the newly created article
    #     for attachment in self.env['ir.attachment'].browse(attachment_ids):
    #         attachment.copy({
    #             'res_model': 'knowledge.article',
    #             'res_id': article.id,
    #         })
    #     return article
