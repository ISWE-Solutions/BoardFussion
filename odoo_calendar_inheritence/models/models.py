from PyPDF2 import PdfReader, PdfWriter
from markupsafe import Markup
from bs4 import BeautifulSoup
import base64
from datetime import time
import logging
import io
import re
from io import BytesIO
import babel
import babel.dates
from markupsafe import Markup, escape
from PIL import Image
from lxml import etree, html
from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError, UserError
from docx import Document
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, ListFlowable, ListItem
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from xml.sax.saxutils import escape
from weasyprint import HTML

_logger = logging.getLogger(__name__)

CLOSED_STATES = {
    '1_done': 'Done',
    '1_canceled': 'Canceled',
}


class OdooCalendarInheritence(models.Model):
    _inherit = 'calendar.event'

    milestone_id = fields.Many2one('project.milestone', string='Milestone')
    agenda_description = fields.Html(name="agenda_description", string="Description")
    mom_description = fields.Html(name="mom_description", string="Description")
    image = fields.Image(name="image", string="Image")
    attachment_ids = fields.Many2many(comodel_name='ir.attachment', string="Attachments")
    video_attachment_ids = fields.One2many(comodel_name='video.attachment', inverse_name='calendar_id',
                                           string="Attachments")
    parent_id = fields.Many2one('calendar.event', string='Parent Task', index=True, tracking=True)
    child_ids = fields.One2many('calendar.event', 'parent_id', string="Sub-tasks")

    project_id = fields.Many2one('project.project', string='Project',
                                 domain="['|', ('company_id', '=', False), ('company_id', '=?',  company_id)]",
                                 index=True, tracking=True, change_default=True)
    display_in_project = fields.Boolean(default=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'High'),
    ], default='0', index=True, string="Priority", tracking=True)
    state = fields.Selection([
        ('01_in_progress', 'In Progress'),
        ('02_changes_requested', 'Changes Requested'),
        ('03_approved', 'Approved'),
        *CLOSED_STATES.items(),
        ('04_waiting_normal', 'Waiting'),
    ], string='State', copy=False, default='01_in_progress', required=True,
        readonly=False, index=True, recursive=True, tracking=True)
    name = fields.Char(string='Title', tracking=True, required=False, index='trigram')
    subtask_count = fields.Integer("Sub-task Count")
    closed_subtask_count = fields.Integer("Closed Sub-tasks Count")
    partner_id = fields.Many2one('res.partner',
                                 string='Customer', recursive=True, tracking=True, store=True, readonly=False,
                                 domain="['|', ('company_id', '=?', company_id), ('company_id', '=', False)]")
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=False, recursive=True, copy=True,
                                 default=lambda self: self.env.user.company_id
                                 )

    tag_ids = fields.Many2many('project.tags', string='Tags')
    new_project_id = fields.Many2one('project.project', string='Action Point',
                                     domain="['|', ('company_id', '=', False), ('company_id', '=?',  company_id)]")
    new_task_name = fields.Char('Task Title')
    user_ids = fields.Many2many('res.users',
                                string='Assignees', tracking=True, )
    date_deadline = fields.Datetime(string='Deadline', index=True, tracking=True)
    end_date = fields.Datetime(string=' End date', index=True, tracking=True)
    task_id = fields.Many2one('project.task', string='Related Task', domain="[('project_id', '=', new_project_id)]")
    new_task_id = fields.Char(string="Task Name")
    stage_id = fields.Many2one('project.task.type', string='Stage', domain="[('project_ids', '=', new_project_id)]",
                               readonly=False, ondelete='restrict', tracking=True, index=True)
    agenda_lines_ids = fields.One2many(comodel_name='agenda.lines', inverse_name='calendar_id', string='Lines')
    product_line_ids = fields.One2many(comodel_name='calendar.event.product.line', inverse_name='calendar_id',
                                       string='Agenda Lines')
    product_document_ids = fields.Many2many(comodel_name='product.document', compute='_compute_product_documents',
                                            string='Product Documents')
    article_exists = fields.Boolean(compute='_compute_article_exists', store=False)
    article_id = fields.Many2one('knowledge.article', string='Related Article')
    description_article_id = fields.Many2one('knowledge.article', string='Related Description Article')
    task_created = fields.Boolean(string="Task Created", default=False)
    description = fields.Html(string="Description")
    attendees_lines_ids = fields.One2many('attendees.lines', 'calendar_id')
    has_attendees_added = fields.Boolean(default=False)
    has_attendees_confirmed = fields.Boolean(default=False)
    last_write_count = fields.Integer('Last Count')
    last_write_date = fields.Datetime('Last Write Date')
    product_id = fields.Many2one('product.template', string="Product")
    nested_calender = fields.Boolean(default=False)
    agenda_lines_count = fields.Integer(string="Agendas", compute='_compute_agenda_count')
    mom_lines_count = fields.Integer(string="Minutes of Meeting", compute='_compute_mom_count')
    action_point_count = fields.Integer(string="Action Points", compute='_compute_action_count')
    company_logo = fields.Image()
    is_meeting_finished = fields.Boolean(default=False)
    is_description_created = fields.Boolean(default=False)
    document_count = fields.Integer(compute='_compute_document_count')
    agenda_ids = fields.One2many('agenda.lines', 'calendar_id', string='Agenda Items')
    # calendar_id = fields.Many2one('calendar.event.product.line', string="Calendar Event", required=True)
    Restricted = fields.Many2many(
        'res.partner',
        'calendar_event_res_partner_rel',  # Unique relation table name
        string="Document Restricted Visibility",
        store=True
    )
    #
    # @api.depends('calendar_id', 'calendar_id.Restricted')
    # def _compute_restricted(self):
    #     for record in self:
    #         if record.calendar_id:
    #             # Log the related Restricted values for debugging
    #             print(f"Related Restricted values: {record.calendar_id.Restricted}")
    #             record.Restricted = record.calendar_id.Restricted
    #         else:
    #             record.Restricted = False

    # Restricted = fields.Many2many(
    #     'res.partner',
    #     'calendar_event_res_partner_restricted_rel',  # Custom relation table name
    #     string="Document visibility",
    #     tracking=True
    # )

    # is_user_restricted = fields.Boolean(compute='_compute_is_user_restricted', store=False)
    #
    # @api.depends('Restricted')
    # def _compute_is_user_restricted(self):
    #     for record in self:
    #         record.is_user_restricted = self.env.user.partner_id in record.Restricted

    # visibility
    privacy = fields.Selection(
        [('public', 'Public'),
         ('private', 'Private'),
         ('confidential', 'Only internal users')],
        'Privacy', default='private', required=True,
        help="People to whom this event will be visible.")

    @api.depends('product_line_ids')
    def _compute_agenda_count(self):
        for rec in self:
            if rec.product_line_ids:
                rec.agenda_lines_count = len(rec.product_line_ids)
            else:
                rec.agenda_lines_count = 0

    def _compute_action_count(self):
        for rec in self:
            if rec.project_id:
                rec.action_point_count = rec.project_id.task_count
            else:
                rec.action_point_count = 0

    @api.depends('attendees_lines_ids')
    def _compute_mom_count(self):
        count = 0
        for rec in self:
            if rec.attendees_lines_ids:
                for attendee in rec.attendees_lines_ids:
                    if attendee.has_attended:
                        count += 1
                rec.mom_lines_count = count
            else:
                rec.mom_lines_count = 0

    # def _compute_mom_count(self):
    #     pass

    # ----------------------------------------------------------------------------
    #                               Calendar --> Documents
    # ----------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, values):
        print("MAIN CREATE")
        # for value in values:
        #     if not value.get('name') or value['name'] == _('new'):
        #
        #         # self._check_unique_agenda(value['agenda'])
        # print(self._context.get('dont_create_nested'))
        for rec in values:
            if not rec.get('nested_calender'):
                # print("Here NOT")
                seq_product = self.env['ir.sequence'].next_by_code('knowledge.article.sequence')
                product_values = {
                    'name': seq_product,
                    'categ_id': self.env.ref("odoo_calendar_inheritence.product_category_dummy").id,
                }
                create_product = self.env['product.template'].sudo().create(product_values)
                rec['product_id'] = create_product.id
                if rec.get('name'):
                    project_values = {
                        'name': rec.get('name'),
                    }
                    create_project = self.env['project.project'].sudo().create(project_values)
                    rec['project_id'] = create_project.id
                else:
                    # print("Else")
                    project_values = {
                        'name': 'New Project',
                    }
                    create_project = self.env['project.project'].sudo().create(project_values)
                    rec['project_id'] = create_project.id

                stage_data = [
                    {'name': 'New', 'project_ids': [(4, create_project.id)]},
                    {'name': 'In Progress', 'project_ids': [(4, create_project.id)]},
                    {'name': 'Finished', 'project_ids': [(4, create_project.id)]}
                ]
                for stage in stage_data:
                    self.env['project.task.type'].sudo().create(stage)
        rtn = super(OdooCalendarInheritence, self).create(values)

        return rtn

    # ----------------------------------------------------------------------------
    # ----------------------------------------------------------------------------

    def write(self, vals):
        if 'name' in vals:
            if self.project_id:
                self.project_id.sudo().write({
                    'name': vals['name']
                })
        res = super(OdooCalendarInheritence, self).write(vals)
        return res

    @api.depends('article_id')
    def _compute_article_exists(self):
        for record in self:
            record.article_exists = bool(record.article_id)

    def _get_src_data_b64(self, value):
        try:  # FIXME: maaaaaybe it could also take raw bytes?
            image = Image.open(BytesIO(base64.b64decode(value)))
            image.verify()

        except IOError:
            raise ValueError("Non-image binary fields can not be converted to HTML")
        except:  # image.verify() throws "suitable exceptions", I have no idea what they are
            raise ValueError("Invalid image content")

        return "data:%s;base64,%s" % (Image.MIME[image.format], value.decode('ascii'))


    def create_article_calendar(self):
        if not self.product_line_ids:
            raise ValidationError("Please add an agenda before making an Article!")

        counter = 1
        company_id = self.env.company
        product_id = self.product_id.id
        logo = company_id.logo
        if logo:
            logo_html = Markup('<img src="%s" class="bg-view" alt="Company Logo"/>') % self._get_src_data_b64(logo)
        else:
            logo_html = ''

        html_content = Markup("""
                    <table class="table">
                        <thead>
                            <tr style="border: 0px; background-color: #ffffff;">
                                <th style="padding: 10px; border: 0px;">ID</th>
                                <th style="padding: 10px; border: 0px;">Agenda Item</th>
                                <th style="padding: 10px; border: 0px;">Presenter</th>
                            </tr>
                        </thead>
                        <tbody id="article_body">
        """)

        for line in self.product_line_ids:
            presenters = ', '.join(presenter.name for presenter in line.presenter_id)
            html_content += Markup("""
                <tr style="border: 0px;">
                    <td style="padding: 10px; border: 0px;">{counter}</td>
                    <td style="padding: 10px; border: 0px;">{description}</td>
                    <td style="padding: 10px; border: 0px;">{presenters}</td>
                </tr>
            """).format(
                counter=counter,
                description=line.description or 'N/A',
                presenters=presenters or 'N/A'
            )

            counter += 1

        html_content += Markup("""
                        </tbody>
                    </table>
                    """)

        body_content = Markup("""
            <div>
                <header style="text-align: center;">
                    {logo_html}<br><br>
                    <h2><strong>{company_name}<strong></h2>
                </header>
                <div class="container">
                    <div class="card-body border-dark">
                        <div class="row no-gutters align-items-center">
                            <div class="col align-items-center">
                                <p class="mb-0">
                                    <span> {company_street} </span>
                                </p>
                                <p class="mb-0">
                                   <span> {company_city} </span>
                                </p>
                                <p class="m-0">
                                   <span> {company_country} </span>
                                </p>
                            </div>
                            <div class="col-auto">
                                <div class="float-right text-end">
                                    <p class="mb-0 float-right">
                                        <span> {company_phone} </span>
                                        <i class="fa fa-phone-square ms-2 text-info" title="Phone"/>
                                    </p>
                                    <p class="mb-0 float-right">
                                       <span> {company_email} </span>
                                        <i class="fa fa-envelope ms-2 text-info" title="Email"/>
                                    </p>
                                    <p class="mb-0 float-right">
                                        <span> {company_website} </span>
                                        <i class="fa fa-globe ms-2 text-info" title="Website"/>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div><br><hr>
                <div class="container">
                <p><strong style='font-size: 14px;'>Title: </strong> {event_name}</p>
                <p><strong>Start Date:</strong> {start_date}</p>
                <p><strong>Organizer:</strong> {organizer}</p>
                <p><strong>Subject:</strong> {description}</p>
                </div>
                <hr/>
                {html_content}
            </div>
        """).format(
            logo_html=logo_html,
            company_name=company_id.name,
            company_street=company_id.street,
            company_city=company_id.city,
            company_country=company_id.country_id.name,
            company_phone=company_id.phone,
            company_email=company_id.email,
            company_website=company_id.website,
            event_name=self.name,
            start_date=self.start_date if self.start_date else ' ',
            organizer=self.user_id.name,
            description=self.description,
            html_content=html_content
        )

        article_values = {
            'name': Markup("Agenda: {event_name}").format(event_name=self.name),
            'body': body_content,
            'calendar_id': self.id,
        }

        article = self.env['knowledge.article'].sudo().create(article_values)
        self.article_id = article.id

        self.article_id.product_id = self.product_id.id
        self.last_write_count = len(self.product_line_ids)
        self.last_write_date = fields.Datetime.now()

    def action_add_knowledge_article(self):
        if not self.article_id:
            raise ValidationError("No Article for these records in Knowledge Module!")

        filtered_product_lines_2 = [line for line in self.product_line_ids if line.create_date >= self.last_write_date]

        if not filtered_product_lines_2:
            raise UserError(_("No new data added to the agenda! Please add data before making changes to the article!"))

        existing_content = self.article_id.body
        soup = BeautifulSoup(existing_content, 'html.parser')

        # Find the existing table body
        table_body = soup.find('tbody')
        if not table_body:
            raise UserError(_("No existing table found in the article!"))

        filtered_product_lines = [line for line in self.product_line_ids if line.create_date < self.last_write_date]
        serial = len(filtered_product_lines) + 1

        for line in self.product_line_ids:
            if line.create_date >= self.last_write_date:
                presenters = ', '.join(presenter.name for presenter in line.presenter_id)

                # Strip HTML tags from the description and preserve line breaks
                description_soup = BeautifulSoup(line.description or 'N/A', 'html.parser')
                description_text = description_soup.get_text()
                description_text = description_text.replace('\n', '<br>')

                new_row = soup.new_tag('tr', style="border: 0px;")

                serial_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
                serial_td.string = str(serial)
                new_row.append(serial_td)

                description_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
                description_td.append(BeautifulSoup(description_text, 'html.parser'))
                new_row.append(description_td)

                presenters_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
                presenters_td.string = presenters or 'N/A'
                new_row.append(presenters_td)

                table_body.append(new_row)
                serial += 1

        self.last_write_date = fields.Datetime.now()

        # Convert the modified soup object back to a string
        updated_content = str(soup)

        article_values = {
            'body': Markup(updated_content),
        }
        self.article_id.sudo().write(article_values)

    # def action_add_knowledge_article(self):
    #         if not self.article_id:
    #             raise ValidationError("No Article for these records in Knowledge Module!")
    #
    #         filtered_product_lines_2 = [line for line in self.product_line_ids if
    #                                     line.create_date >= self.last_write_date]
    #
    #         if not filtered_product_lines_2:
    #             raise UserError(
    #                 _("No new data added to the agenda! Please add data before making changes to the article!"))
    #
    #         existing_content = self.article_id.body
    #         soup = BeautifulSoup(existing_content, 'html.parser')
    #
    #         # Find the existing table body
    #         table_body = soup.find('tbody')
    #         if not table_body:
    #             raise UserError(_("No existing table found in the article!"))
    #
    #         filtered_product_lines = [line for line in self.product_line_ids if line.create_date < self.last_write_date]
    #         serial = len(filtered_product_lines) + 1
    #
    #         for line in self.product_line_ids:
    #             if line.create_date >= self.last_write_date:
    #                 presenters = ', '.join(presenter.name for presenter in line.presenter_id)
    #
    #                 new_row = soup.new_tag('tr', style="border: 0px;")
    #
    #                 serial_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
    #                 serial_td.string = str(serial)
    #                 new_row.append(serial_td)
    #
    #                 description_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
    #                 description_td.string = line.description or 'N/A'
    #                 new_row.append(description_td)
    #
    #                 presenters_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
    #                 presenters_td.string = presenters or 'N/A'
    #                 new_row.append(presenters_td)
    #
    #                 table_body.append(new_row)
    #                 serial += 1
    #
    #         self.last_write_date = fields.Datetime.now()
    #
    #         # Convert the modified soup object back to a string
    #         updated_content = str(soup)
    #
    #         article_values = {
    #             'body': Markup(updated_content),
    #         }
    #         self.article_id.sudo().write(article_values)

    # def action_add_knowledge_article(self):
    #     if not self.article_id:
    #         raise ValidationError("No Article for these records in Knowledge Module!")
    #
    #     filtered_product_lines_2 = [line for line in self.product_line_ids if line.create_date >= self.last_write_date]
    #
    #     if not filtered_product_lines_2:
    #         raise UserError(_("No new data added to the agenda! Please add data before making changes to the article!"))
    #
    #     existing_content = self.article_id.body
    #     soup = BeautifulSoup(existing_content, 'html.parser')
    #
    #     # Find the existing table body
    #     table_body = soup.find('tbody')
    #     if not table_body:
    #         raise UserError(_("No existing table found in the article!"))
    #
    #     filtered_product_lines = [line for line in self.product_line_ids if line.create_date < self.last_write_date]
    #     serial = len(filtered_product_lines) + 1
    #
    #     for line in self.product_line_ids:
    #         if line.create_date >= self.last_write_date:
    #             presenters = ', '.join(presenter.name for presenter in line.presenter_id)
    #
    #             # Strip HTML tags from the description
    #             description_soup = BeautifulSoup(line.description or 'N/A', 'html.parser')
    #             description_text = description_soup.get_text()
    #
    #             new_row = soup.new_tag('tr', style="border: 0px;")
    #
    #             serial_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
    #             serial_td.string = str(serial)
    #             new_row.append(serial_td)
    #
    #             description_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
    #             description_td.string = description_text
    #             new_row.append(description_td)
    #
    #             presenters_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
    #             presenters_td.string = presenters or 'N/A'
    #             new_row.append(presenters_td)
    #
    #             table_body.append(new_row)
    #             serial += 1
    #
    #     self.last_write_date = fields.Datetime.now()
    #
    #     # Convert the modified soup object back to a string
    #     updated_content = str(soup)
    #
    #     article_values = {
    #         'body': Markup(updated_content),
    #     }
    #     self.article_id.sudo().write(article_values)

    def action_create_agenda_descriptions(self):
        company_id = self.env.company
        # Get the company logo
        logo = company_id.logo
        if logo:
            logo_html = Markup('<img src="%s" class="bg-view" alt="Company Logo"/>') % self._get_src_data_b64(logo)
            # print(logo_html)
        if not self.product_line_ids:
            raise ValidationError("Please add data before making an Article!")
        if not self.description_article_id:
            counter = 1
            company_id = self.env.company
            mom_description_content = Markup("""""")
            attendees_names = Markup("""""")

            # Build the table rows for each agenda line
            for line in self.product_line_ids:
                mom_description_content += Markup("""
                            {description}<hr>
                            """).format(
                    description=line.description or 'N/A'
                )
                counter += 1
            attendees = self.action_confirm_attendees()
            self.has_attendees_confirmed = True
            if attendees:
                attendees_names += Markup("""
                                                    <strong>Meeting Attendees:</strong><br><br>
                """)
            for attendee in attendees:
                if attendee:
                    attendees_names += Markup("""
                                    {attendee_name}<br>
                """).format(attendee_name=attendee.attendee_name)
            attendees_names += Markup("""
                        <hr>
                """)

            body_content = Markup("""
                <div>
                    <header style="text-align: center;">
                        {logo_html}<br><br>
                        <h2><strong>{company_name}<strong></h2>
                    </header>
                    <div class="container">
                        <div class="card-body border-dark">
                            <div class="row no-gutters align-items-center">
                                <div class="col align-items-center">
                                    <!-- Name and position -->
                                    <p class="mb-0">
                                        <span> {company_street} </span>
                                    </p>
                                    <p class="mb-0">
                                        <span> {company_city} </span>
                                    </p>
                                    <p class="m-0">
                                        <span> {company_country} </span>
                                    </p>
                                </div>
                                <div class="col-auto">
                                    <!-- Phone and email -->
                                    <div class="float-right text-end">
                                        <p class="mb-0 float-right">
                                            <span> {company_phone} </span>
                                            <i class="fa fa-phone-square ms-2 text-info" title="Phone"/>
                                        </p>
                                        <p class="mb-0 float-right">
                                            <span> {company_email} </span>
                                            <i class="fa fa-envelope ms-2 text-info" title="Email"/>
                                        </p>
                                        <p class="mb-0 float-right">
                                            <span> {company_website} </span>
                                            <i class="fa fa-globe ms-2 text-info" title="Website"/>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div><br><hr>
                    {attendees_names}
                    <br>
                    {mom_description_content}
                </div>
            """).format(
                logo_html=logo_html,
                company_name=company_id.name,
                company_street=company_id.street,
                company_city=company_id.city,
                company_country=company_id.country_id.name,
                company_phone=company_id.phone,
                company_email=company_id.email,
                company_website=company_id.website,
                attendees_names=attendees_names,
                mom_description_content=mom_description_content,
            )
            article_values = {
                'name': f"Minutes: {self.name}",  # Name for the description, for that Agenda!
                'body': body_content,
                'calendar_id': self.id,
            }

            description_article = self.env['knowledge.article'].sudo().create(article_values)
            self.description_article_id = description_article
            self.description_article_id.product_id = self.product_id.id
            self.is_description_created = True
            self.description_article_id.is_minutes_of_meeting = True
            return self.action_view_description_article()
        else:
            return self.action_view_description_article()

    def action_view_knowledge_article(self):
        self.ensure_one()
        for record in self:
            if record.article_id:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Knowledge Article',
                    'res_model': 'knowledge.article',
                    'view_mode': 'form',
                    'res_id': record.article_id.id,
                    'target': 'current',
                }

    def action_view_description_article(self):
        self.ensure_one()
        if self.description_article_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Knowledge Article',
                'res_model': 'knowledge.article',
                'view_mode': 'form',
                'res_id': self.description_article_id.id,
                'target': 'current',
            }

    # -------------------------------------------------------------------
    # -------------------------------------------------------------------
    #
    # @api.depends('product_line_ids')
    # def _compute_product_documents(self):
    #     for event in self:
    #         product_ids = event.product_line_ids.mapped('product_id')
    #         documents = self.env['product.document'].search([('product_id', 'in', product_ids.ids)])
    #         event.product_document_ids = [5, 0, [documents.ids]]

    @api.depends('product_line_ids')
    def _compute_product_documents(self):
        for event in self:
            product_ids = event.product_line_ids.mapped('product_id')
            print(f"Computing product documents for event {event.id}, product_ids: {product_ids.ids}")
            if product_ids:
                documents = self.env['product.document'].search([('product_id', 'in', product_ids.ids)])
                print(f"Found documents: {documents.ids} for product_ids: {product_ids.ids}")
                event.product_document_ids = [(6, 0, documents.ids)]
            else:
                event.product_document_ids = [(5,)]  # Clear if no products
                print(f"No products found for event {event.id}, clearing documents.")

    @api.onchange('new_project_id')
    def _onchange_new_project_id(self):
        if self.new_project_id:
            return {'domain': {'task_id': [('project_id', '=', self.new_project_id.id)]}}
        else:
            return {'domain': {'task_id': []}}

    def action_create_task(self):
        for record in self:
            if record.new_project_id and record.new_task_name:
                task_vals = {
                    'name': record.new_task_name,
                    'project_id': record.new_project_id.id,
                    'user_ids': [(6, 0, record.user_ids.ids)],
                    'date_deadline': record.date_deadline,
                    'stage_id': record.stage_id.id if record.stage_id else False,
                    'parent_id': False,
                }
                new_task = self.env['project.task'].create(task_vals)
                record.task_id = new_task.id
                record.task_created = True  # Set task_created to True

    def action_view_task(self):
        for record in self:
            if record.task_id:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Task',
                    'view_mode': 'form',
                    'res_model': 'project.task',
                    'res_id': record.task_id.id,
                    'target': 'current',
                }

    def action_reset_attendees(self):
        for rec in self:
            rec.attendees_lines_ids.unlink()
            rec.is_description_created = False
            rec.has_attendees_added = False
            rec.has_attendees_confirmed = False
            rec.description_article_id.sudo().unlink()

    def action_add_attendees(self):
        partners = []
        for partner in self.partner_ids:
            partners.append(
                Command.create(
                    {
                        'attendee_name': partner.name,
                        'email': partner.email,
                        'phone': partner.phone,
                    }
                )
            )
        if not self.attendees_lines_ids:
            self.attendees_lines_ids = partners
            self.has_attendees_added = True
        # ￼
        else:
            self.attendees_lines_ids.sudo().unlink()
            self.attendees_lines_ids = partners
            self.has_attendees_added = True

    def _calendar_meeting_end_tracker(self):
        calendar_meetings = self.env['calendar.event'].search([])
        if calendar_meetings:
            for record in calendar_meetings:
                if not record.allday:
                    if record.stop and record.stop <= fields.Datetime.now():
                        record.is_meeting_finished = True
                    else:
                        record.is_meeting_finished = False
                if record.allday:
                    if record.stop_date and record.stop_date <= fields.Date.today():
                        record.is_meeting_finished = True
                    else:
                        record.is_meeting_finished = False

    def action_confirm_attendees(self):
        attendees = []
        if not self.attendees_lines_ids:
            raise UserError(_('Kindly, add the attendees!'))
        for attendee in self.attendees_lines_ids:
            if attendee.has_attended:
                attendees.append(attendee)
        return attendees

        # self.attendees_lines_ids =

    def _compute_document_count(self):
        active_user = self.env.user.partner_id.id
        domain = [
            '|',
            '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.id),
            '&',
            ('res_model', '=', 'product.template'),
            ('res_id', 'in', self.product_id.product_variant_ids.ids),
            ('partner_ids', 'in', [active_user]), ]
        documents = self.env['product.document'].sudo().search(domain)
        # print(documents)
        self.document_count = len(documents)

    # def action_open_documents(self):
    #     # self.ensure_one()
    #     company_id = self.env.company.id
    #     current_time = fields.Datetime.now()
    #     meeting_end_time = self.stop
    #     active_user = self.env.user.partner_id.id
    #     domain = [
    #         '|',
    #         '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.id),
    #         '&',
    #         ('res_model', '=', 'product.template'),
    #         ('res_id', 'in', self.product_id.product_variant_ids.ids),
    #         ('partner_ids', 'in', [active_user]), ]
    #     # if current_time and meeting_end_time:
    #     # if current_time >= meeting_end_time: #If Meeting Has Ended
    #     #     domain = [
    #     #         '|',
    #     #         '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.id),
    #     #         '&',
    #     #         ('res_model', '=', 'product.template'),
    #     #         ('res_id', 'in', self.product_id.product_variant_ids.ids),
    #     #     ]
    #     # else: #If meeting is still going!
    #     #     domain = [
    #     #         '|',
    #     #         '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_id.id),
    #     #         '&',
    #     #         ('res_model', '=', 'product.template'),
    #     #         ('res_id', 'in', self.product_id.product_variant_ids.ids),
    #     #         ('partner_ids', 'in', [active_user]),
    #
    #     for rec in self:
    #         return {
    #             'name': _('Documents'),
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'product.document',
    #             'view_mode': 'kanban,tree,form',
    #             'context': {
    #                 'default_res_model': rec.product_id._name,
    #                 'default_res_id': rec.product_id.id,
    #                 'default_company_id': company_id,
    #             },
    #             'domain': domain,
    #             'target': 'current',
    #             'help': """
    #                 <p class="o_view_nocontent_smiling_face">
    #                     %s
    #                 </p>
    #                 <p>
    #                     %s
    #                     <br/>
    #                 </p>
    #             """ % (
    #                 _("Upload Documents to your agenda"),
    #                 _("Use this feature to store Documents you would like to share with your members"),
    #             )
    #         }

    def action_open_documents(self):
        self.ensure_one()

        # Collect attachment IDs from all product lines' `pdf_attachment` fields
        attachment_ids = []
        for line in self.product_line_ids:
            if not line.is_user_restricted:
                attachment_ids.extend(line.pdf_attachment.ids)

        if not attachment_ids:
            _logger.info("No accessible attachments for user %s on event %s", self.env.user.name, self.name)
            return {'type': 'ir.actions.act_window_close'}  # Close action if no accessible attachments

        # Search for documents based on the collected attachment IDs
        matching_documents = self.env['product.document'].search([('ir_attachment_id', 'in', attachment_ids)])

        _logger.info("Matching Product Document IDs: %s", matching_documents.ids)

        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.document',
            'view_mode': 'kanban,tree,form',
            'context': {
                'default_res_model': 'product.template',
                'default_company_id': self.env.company.id,
            },
            'domain': [('ir_attachment_id', 'in', attachment_ids)],
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

    def action_points_kanban(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Action Points Kanban View',
            'view_mode': 'kanban,form,tree',
            'res_model': 'project.task',
            'target': 'current',
            'domain': [('project_id', '=', self.project_id.id)],
            'context': {'default_project_id': self.project_id.id},
        }

    def action_open_custom_composer(self):
        if not self.partner_ids:
            raise UserError(_("There are no attendees on these events"))
        template_id = self.env['ir.model.data']._xmlid_to_res_id('appointment.appointment_booked_mail_template',
                                                                 raise_if_not_found=False)
        # The mail is sent with datetime corresponding to the sending user TZ
        default_composition_mode = self.env.context.get('default_composition_mode',
                                                        self.env.context.get('composition_mode', 'comment'))
        compose_ctx = dict(
            default_composition_mode=default_composition_mode,
            default_model='calendar.event',
            default_res_ids=self.ids,
            default_template_id=template_id,
            default_partner_ids=self.partner_ids.ids,
            mail_tz=self.env.user.tz,
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contact Attendees'),
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': compose_ctx,
        }

    @api.onchange('partner_ids')
    def compute_visible_users(self):
        for record in self:
            if record.product_id and record.partner_ids:
                record.product_id.product_document_ids.sudo().write(
                    {
                        'partner_ids': [(6, 0, record.partner_ids.ids)]
                    }
                )

    def action_agenda_inv_sendmail(self):
        email = self.env.user.email
        if email:
            for meeting in self:
                meeting.attendee_ids._send_custom_mail_to_attendees(
                    self.env.ref('odoo_calendar_inheritence.calendar_template_agenda_meeting_invitation',
                                 raise_if_not_found=False)
                )
        return True

    # def unlink(self):
    #     # Raise a warning before deletion
    #     for event in self:
    #         message = _(
    #             "Action points, documents, agenda, and minutes will be permanently deleted. Are you sure you want to continue?")
    #         raise UserError(message)
    #
    #     # If confirmed, perform the standard deletion
    #     return super(OdooCalendarInheritence, self).unlink()

    def copy(self, default=None):
        default = dict(default or {})

        # Append "(copy)" to the event name
        if 'name' not in default:
            default['name'] = f"{self.name} (copy)"

        print(f"Starting to copy calendar event: {self.id}")

        # Ensure related product lines are copied
        if self.product_line_ids:
            new_product_lines = []
            for line in self.product_line_ids:
                # Duplicate each line and append to new_product_lines
                new_line = line.copy()
                new_product_lines.append((4, new_line.id))  # (4, ID) to link new record
                print(f"Copied product line: {line.id} -> {new_line.id}")

            default['product_line_ids'] = new_product_lines

        # Ensure related agenda items are copied
        if self.agenda_lines_ids:
            print(f"Agenda lines found for event {self.id}: {[agenda.id for agenda in self.agenda_lines_ids]}")
            new_agenda_lines = []
            for agenda_item in self.agenda_lines_ids:
                # Duplicate each agenda item without calendar_id
                new_agenda_item = agenda_item.copy(default={'calendar_id': False})
                new_agenda_lines.append((4, new_agenda_item.id))  # (4, ID) to link new record

                # Link existing attachments directly without duplicating
                existing_attachments = [(4, attachment.id) for attachment in agenda_item.agenda_attachment_ids]
                new_agenda_item.write({
                    'agenda_attachment_ids': existing_attachments  # Link existing attachments
                })
                print(f"Copied agenda item: {agenda_item.id} -> {new_agenda_item.id}")

            default['agenda_lines_ids'] = new_agenda_lines
        else:
            print(f"No agenda lines found for event {self.id}.")

        # Perform standard duplication
        print("Performing standard duplication...")
        return super(OdooCalendarInheritence, self).copy(default)

    def image_to_pdf(self, image_data):
        """
        Convert image data to a PDF binary.
        """
        from io import BytesIO
        from reportlab.pdfgen import canvas

        # Decode the base64 image data
        image_stream = BytesIO(base64.b64decode(image_data))
        image = ImageReader(image_stream)

        # Create a PDF in memory
        buffer = BytesIO()
        pdf_canvas = canvas.Canvas(buffer)

        # Get image dimensions
        width, height = image.getSize()

        # Set the page size to match the image dimensions
        pdf_canvas.setPageSize((width, height))

        # Draw the image on the canvas
        pdf_canvas.drawImage(image, 0, 0, width=width, height=height)

        pdf_canvas.save()

        # Return the binary PDF content
        buffer.seek(0)
        return buffer.read()

    def docx_to_pdf(self, docx_data):
        """
        Convert a DOCX file (binary data) to a properly formatted PDF
        with support for text alignment, spacing, and list numbering/bullets.
        """
        # Decode and load the DOCX file from base64-encoded data
        doc = Document(BytesIO(base64.b64decode(docx_data)))

        # Prepare a PDF stream to write to
        pdf_stream = BytesIO()
        pdf = SimpleDocTemplate(
            pdf_stream,
            pagesize=letter,
            leftMargin=inch,
            rightMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )

        # Define styles for the PDF
        styles = getSampleStyleSheet()

        # Add custom styles only if they are not already defined
        if 'Center' not in styles:
            styles.add(ParagraphStyle(name='Center', alignment=1))  # Center-aligned
        if 'Right' not in styles:
            styles.add(ParagraphStyle(name='Right', alignment=2))  # Right-aligned
        if 'Bold' not in styles:
            styles.add(ParagraphStyle(name='Bold', fontName='Helvetica-Bold'))  # Bold text
        # Do not add 'Italic' since it already exists in the default stylesheet

        story = []  # Content for the PDF

        # Track list numbering
        list_counter = 1
        roman_counter = 1

        for paragraph in doc.paragraphs:
            # Skip empty paragraphs
            if not paragraph.text.strip():
                continue

            # Determine alignment
            if paragraph.alignment == 1:  # Center-aligned
                style = styles['Center']
            elif paragraph.alignment == 2:  # Right-aligned
                style = styles['Right']
            else:  # Default to left-aligned
                style = styles['BodyText']

            # Build the formatted text
            formatted_text = ""
            for run in paragraph.runs:
                text = escape(run.text)  # Escape special characters
                if run.bold:
                    formatted_text += f"<b>{text}</b>"
                elif run.italic:
                    formatted_text += f"<i>{text}</i>"
                else:
                    formatted_text += text

            # Handle list paragraphs
            if paragraph.style.name.lower().startswith('list'):
                if "roman" in paragraph.style.name.lower():  # Roman numeral lists
                    formatted_text = f"{roman_counter}. {formatted_text}"
                    roman_counter += 1
                else:  # Regular numbered lists
                    formatted_text = f"{list_counter}. {formatted_text}"
                    list_counter += 1

                # Add as a list item
                story.append(ListFlowable([ListItem(Paragraph(formatted_text, style))], bulletType='bullet'))
            else:
                # Reset counters for non-list paragraphs
                list_counter = 1
                roman_counter = 1

                # Add the paragraph
                story.append(Paragraph(formatted_text, style))

            # Add spacing between paragraphs
            story.append(Spacer(1, 0.2 * inch))

        # Build the PDF document
        pdf.build(story)

        # Retrieve the binary PDF content
        pdf_stream.seek(0)
        return pdf_stream.read()

    def html_to_pdf(self, html_content):
        """
        Convert HTML content to a PDF using a library like `weasyprint` or `wkhtmltopdf`.
        """
        pdf_stream = io.BytesIO()
        HTML(string=html_content).write_pdf(pdf_stream)
        pdf_stream.seek(0)
        return pdf_stream.getvalue()

    def add_media_placeholder(pdf_writer, media_files):
        """
        Add placeholders for media files in the merged PDF.
        """
        from reportlab.pdfgen import canvas

        for media_file in media_files:
            pdf_page = io.BytesIO()
            pdf_canvas = canvas.Canvas(pdf_page)
            pdf_canvas.drawString(50, 750, f"Media File: {media_file.name}")
            pdf_canvas.drawString(50, 730, f"File Type: {media_file.mimetype}")
            pdf_canvas.drawString(50, 710, "Media files cannot be embedded.")
            pdf_canvas.save()
            pdf_page.seek(0)

            pdf_reader = PdfReader(pdf_page)
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)

    def action_merge_documents(self):
        """
        Merge all supported attachments (PDFs, images, DOCX) from the product lines of the event into a single document.
        """
        self.ensure_one()

        attachments = self.mapped('product_line_ids.pdf_attachment')
        if not attachments:
            raise UserError(_("No attachments found to merge."))

        pdf_writer = PdfWriter()

        for attachment in attachments:
            if attachment.mimetype == 'application/pdf':
                # Add PDF to writer
                pdf_data = base64.b64decode(attachment.datas)
                pdf_reader = PdfReader(io.BytesIO(pdf_data))
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            elif attachment.mimetype.startswith('image/'):
                # Convert image to PDF and add
                pdf_data = self.image_to_pdf(attachment.datas)
                pdf_reader = PdfReader(io.BytesIO(pdf_data))
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            elif attachment.mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                # Convert DOCX to PDF and add
                pdf_data = self.docx_to_pdf(attachment.datas)
                pdf_reader = PdfReader(io.BytesIO(pdf_data))
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            else:
                # Add placeholder for unsupported media files
                self.add_media_placeholder(pdf_writer, [attachment])

        if not pdf_writer.pages:
            raise UserError(_("No valid documents found in attachments."))

        # Write the merged PDF to a stream
        merged_pdf_stream = io.BytesIO()
        pdf_writer.write(merged_pdf_stream)
        merged_pdf_stream.seek(0)

        # Create a new attachment with the merged content
        merged_attachment = self.env['ir.attachment'].create({
            'name': f'Merged Document - {self.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(merged_pdf_stream.read()),
            'mimetype': 'application/pdf',
            'res_model': 'calendar.event',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{merged_attachment.id}',
            'target': 'new',
        }

    def action_view_documents(self):
        self.ensure_one()

        # Collect all `pdf_attachment` documents from the product lines
        attachment_ids = self.mapped('calendar_event_product_line_ids.pdf_attachment').ids

        if not attachment_ids:
            raise ValidationError(_("No documents available to view."))

        # Open the documents in a list view
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', attachment_ids)],
            'target': 'current',
            'context': {
                'default_res_model': 'calendar.event',
                'default_res_id': self.id,
            },
        }


class AgendaLines(models.Model):
    _name = 'agenda.lines'
    _description = 'Agenda Lines'

    calendar_id = fields.Many2one('calendar.event', string="Calendar")
    description = fields.Html(related='calendar_id.agenda_description')
    partner_ids = fields.Many2many('res.partner', string='Attendees')
    duration = fields.Float(related="calendar_id.duration", string='Duration')
    agenda_attachment_ids = fields.Many2many(comodel_name='ir.attachment', string="Attachments")
