from markupsafe import Markup
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
import base64

class CalendarEventProductLine(models.Model):
    _name = 'calendar.event.product.line'
    _description = 'Calendar Event Product Line'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    # calendar_id = fields.Many2one('calendar.event', string="Calendar Event")
    product_id = fields.Many2one('product.template', string="Product")
    quantity = fields.Float(string="Quantity")
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    agenda = fields.Char(string='Agenda', default=_('new'))
    presenter_id = fields.Many2many('res.users', string="Presenter", tracking=True)
    duration = fields.Float(string="Duration")
    start_date = fields.Datetime(string='Start Date', default=lambda self: fields.Datetime.now())
    end_date = fields.Datetime(string='End Date')
    description = fields.Html(string='Description')
    time = fields.Char(string='Time')
    pdf_attachment = fields.Many2many('ir.attachment', string='Add Attachments')
    calendar_id = fields.Many2one('calendar.event', string="Calendar Event", required=True)

    Restricted = fields.Many2many(
        'res.partner',
        'calendar_event_product_line_res_partner_rel',  # Unique relation table name
        string="Document Restricted Visibility",
        store=True
    )

    is_user_restricted = fields.Boolean(compute='_compute_is_user_restricted', store=False)

    @api.depends('Restricted')
    def _compute_is_user_restricted(self):
        for record in self:
            record.is_user_restricted = self.env.user.partner_id in record.Restricted

    document_names = fields.Char(string="Document Names", compute="_compute_document_names", store=False)

    @api.depends('pdf_attachment')
    def _compute_document_names(self):
        for line in self:
            document_names = line.pdf_attachment.mapped('name')
            line.document_names = ', '.join(document_names)

    @api.model_create_multi
    def create(self, values):
        rtn = super(CalendarEventProductLine, self).create(values)
        document_model = self.env['product.document']
        for record in rtn:
            record.product_id = record.calendar_id.product_id.id
            product = record.product_id
            if record.pdf_attachment:
                for attachment in record.pdf_attachment:
                    attachment_data = attachment.datas
                    new_document = document_model.sudo().create(
                        {
                            'res_model': 'product.template',
                            'name': attachment.name,
                            'res_id': product.id,
                            'ir_attachment_id': attachment.id,
                        }
                    )
                record.calendar_id.compute_visible_users()
        return rtn

    def write(self, values):

        if 'agenda' in values and values['agenda']:
            self._check_unique_agenda(values['agenda'], self.id)
        # print('------------------->',values)
        if 'pdf_attachment' in values:
            create_doc=[]
            create_list_ids=[]
            unlink_doc=[]
            unlink_list_ids=[]

            for attachment in values['pdf_attachment']:
                if attachment[0] == 4:
                    rec_id=attachment[1]
                    create_list_ids.append(rec_id)

                elif attachment[0] == 3:
                    rec_id = attachment[1]
                    is_remove = True
                    unlink_list_ids.append(rec_id)
                    # doc = self.env['ir.attachment'].browse(unlink_list_ids)
            if create_list_ids:
                att = self.env['ir.attachment'].browse(create_list_ids)
                for rec in att:
                    attachment_data =rec.datas
                    attachment_bytes = base64.b64encode(attachment_data)
                    create_doc.append({
                        'res_model': 'product.template',
                        'name': rec.name,
                        'res_id': self.product_id.id,
                        'ir_attachment_id': rec.id
                        # 'user_ids':[(6, 0, self.env.user.id)],
                    })

                if create_doc:
                    doc_res = self.env['product.document'].sudo().create(create_doc)
            if unlink_list_ids:
                res=self.env['product.document'].sudo().search([('ir_attachment_id','in',unlink_list_ids)])
                # print('Unlink--',res)
                if res:
                    res.sudo().unlink()
                # attachment_data = attachment.datas
                # attachment_bytes = base64.b64encode(attachment_data)
        self.calendar_id.compute_visible_users()
        res=super(CalendarEventProductLine, self).write(values)
        # print(res)
        return res


    def unlink(self):
        unlink_list_ids=[]
        for record in self:
            if record.pdf_attachment:
                unlink_res = self.env['product.document'].sudo().search([('ir_attachment_id', 'in', record.pdf_attachment.ids)])
                if unlink_res:
                    unlink_res.sudo().unlink()
        res = super(CalendarEventProductLine,self).unlink()
        return res

    def _create_subtask(self):
        project_task_model = self.env['project.task']
        for line in self:
            project_name = line.calendar_id.name
            project_id = line.calendar_id.project_id.id
            parent_task_id = line.calendar_id.task_id.id if line.calendar_id.task_id else False
            if not project_id:
                raise ValidationError(_('The project is not set for the calendar event.'))
            task_vals = {
                'name': project_name,
                'project_id': project_id,
                # 'parent_id': parent_task_id,
                'description': line.description or '',
                'user_ids':  [(6, 0, line.presenter_id.ids)],
                'date_deadline': line.end_date,
            }
            project_task_model.create(task_vals)

    def action_create_html(self):
        active_id = self.product_id.product_document_ids.id
        company_id = self.env.company.id
        html = Markup('<a href="/web?#active_id=%d&amp;action=qxm_product_pdf_annotation_tool.product_pdf_annotation&amp;cids=%d" style="padding: 5px 10px; color: #FFFFFF; text-decoration: none; background-color: #875A7B; border: 1px solid #875A7B; border-radius: 3px">View</a>') % (active_id, company_id)
        vals = {'name': "PDF test", 'body': html}
        res = self.env['knowledge.article'].sudo().create(vals)
        # print(res)

    def _check_unique_agenda(self, agenda, exclude_id=None):
        domain = [('agenda', '=', agenda)]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        if self.search_count(domain):
            raise ValidationError(_('The agenda "%s" already exists! Please change the name.') % agenda)

    @api.model
    def _delete_unused_dummy_products(self):
        dummy_category = self.env.ref('odoo_calendar_inheritence.product_category_dummy')
        product_lines = self.search([]).mapped('product_id.id')
        products_to_delete = self.env['product.template'].search([
            ('categ_id', '=', dummy_category.id),
            ('id', 'not in', product_lines)
        ])
        products_to_delete.unlink()

    def action_open_documents(self):
        self.ensure_one()
        company_id = self.env.company.id

        # Collect the attachment IDs from the `pdf_attachment` field.
        attachment_ids = self.pdf_attachment.ids

        # Debug prints to track values
        print("Company ID:", company_id)
        print("Current Product Line ID:", self.id)
        print("Attachment IDs in pdf_attachment:", attachment_ids)

        # Check if there are any matching product documents
        matching_documents = self.env['product.document'].search([('ir_attachment_id', 'in', attachment_ids)])
        print("Matching Product Document IDs:", matching_documents.ids)

        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.document',
            'view_mode': 'kanban,tree,form',
            'context': {
                'default_res_model': 'product.template',
                'default_res_id': self.product_id.id,
                'default_company_id': company_id,
            },
            'domain': [
                ('ir_attachment_id', 'in', attachment_ids),
            ],
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
                _("Upload Documents to your agenda"),
                _("Use this feature to store Documents you would like to share with your members"),
            )
        }