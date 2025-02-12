from email.policy import default

from PyPDF2 import PdfReader, PdfWriter
import re
from markupsafe import Markup
from bs4 import BeautifulSoup
import base64
import logging
import io
import os
from io import BytesIO
from markupsafe import Markup, escape
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from reportlab.lib.randomtext import subjects
from lxml import etree
from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError, UserError
from docx import Document
import subprocess
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, ListFlowable, ListItem
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from xml.sax.saxutils import escape
from weasyprint import HTML
from datetime import datetime
import subprocess
import tempfile

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
    minutes_line_ids = fields.One2many(comodel_name='calendar.event.minutes.line', inverse_name='calendar_id',
                                       string='Agenda Lines')
    product_document_ids = fields.Many2many(comodel_name='product.document', compute='_compute_product_documents',
                                            string='Product Documents')
    minutes_document_ids = fields.Many2many(comodel_name='product.document', compute='_compute_minutes_documents',
                                            string='Product Documents')
    article_exists = fields.Boolean(compute='_compute_article_exists', store=False)
    article_non_exists = fields.Boolean(compute='_compute_article_non_exists', store=False)
    article_id = fields.Many2one('knowledge.article', string='Related Article')
    non_confidential_article_id = fields.Many2one('knowledge.article', string='Related Article')
    description_article_id = fields.Many2one('knowledge.article', string='Related Description Article')
    alternate_description_article_id = fields.Many2one('knowledge.article', string='Related NON-confidential Description Article')
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
    is_board_park = fields.Boolean(string="Boardpack exists", default=False)
    agenda_ids = fields.One2many('agenda.lines', 'calendar_id', string='Agenda Items')
    # calendar_id = fields.Many2one('calendar.event.product.line', string="Calendar Event", required=True)
    non_conf_cover_page = fields.Char(help="this field is used in tracking non confidential cover page",
                                      string="Non confidential cover page")

    from_agenda = fields.Char(string="Agenda From", default="Acting Board Secretary and Legal Council", store="True")

    bp_from = fields.Char(help="From field on Boardpark", default="Acting Board Secretary and Legal Counsel")
    Restricted = fields.Many2many(
        'res.partner',
        'calendar_event_res_partner_rel',  # Unique relation table name
        string="Document Restricted Visibility",
        store=True
    )
    action_visibility = fields.Selection([
        ('show', 'upload'),
        ('hide', 'Generate'),
    ], string="Action Visibility", default='show')

    # visibility
    privacy = fields.Selection(
        [('public', 'Public'),
         ('private', 'Private'),
         ('confidential', 'Only internal users')],
        'Privacy', default='private', required=True,
        help="People to whom this event will be visible.")

    employee_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_employee_partner_ids',
        store=False,
        string="Employee Partners"
    )
    has_confidential_agenda_item = fields.Boolean(compute='_compute_has_confidential_agenda_item')
    is_minutes_created = fields.Boolean(string = "Are minutes Generated")
    is_minutes_published = fields.Boolean(string="Are minutes published")
    is_minutes_uploaded = fields.Boolean(string="Are minutes Uploaded")
    is_boardpack_created = fields.Boolean(string="Are Boardpacks Generated")
    create_text= fields.Char(string="true or false",  default="False")

    is_confidential_minutes_uploaded = fields.Boolean(default=False)
    is_non_confidential_minutes_uploaded = fields.Boolean(default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(OdooCalendarInheritence, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                         submenu=submenu)
        if view_type == 'form' and res.get('fields', {}).get('product_line_ids'):
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='product_line_ids']"):
                if self.env.context.get('default_is_boardpack_created'):
                    node.set('create', 'false')
                else:
                    node.set('create', 'true')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    @api.depends('product_line_ids.confidential')
    def _compute_has_confidential_agenda_item(self):
        for event in self:
            event.has_confidential_agenda_item = any(line.confidential for line in event.product_line_ids)

    def _compute_employee_partner_ids(self):
        employees = self.env['hr.employee'].search([])
        self.employee_partner_ids = employees.mapped('address_home_id')

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

    # ----------------------------------------------------------------------------
    #                               Calendar --> Documents
    # ----------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, values):
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

    def update_article_calendar(self):
        return ""

    @api.depends('article_id')
    def _compute_article_exists(self):
        for record in self:
            record.article_exists = bool(record.article_id)

    @api.depends('non_confidential_article_id')
    def _compute_article_non_exists(self):
        for record in self:
            record.article_non_exists = bool(record.non_confidential_article_id)


    def _get_src_data_b64(self, value):
        try:  # FIXME: maaaaaybe it could also take raw bytes?
            image = Image.open(BytesIO(base64.b64decode(value)))
            image.verify()

        except IOError:
            raise ValueError("Non-image binary fields can not be converted to HTML")
        except:  # image.verify() throws "suitable exceptions", I have no idea what they are
            raise ValueError("Invalid image content")

        return "data:%s;base64,%s" % (Image.MIME[image.format], value.decode('ascii'))

    def delete_article(self):
        """ Deletes the linked article and its non-confidential copy if they exist. """
        # if not self.article_id:
        #     raise ValidationError("No associated article found to delete!")

        _logger.info("Deleting Article: %s", self.article_id.name)

        try:
            # Use consistent naming for the non-confidential article
            non_confidential_name = f"Non-Confidential Agenda: {self.name}"
            _logger.info("Searching for Non-Confidential Article with name: %s", non_confidential_name)
            # Delete the main article
            self.article_id.unlink()
            self.non_confidential_article_id.unlink()
            # Clear references on the agenda record
            self.article_id = False
            self.last_write_count = 0
            self.last_write_date = fields.Datetime.now()

            _logger.info("Articles successfully deleted.")
            self.remove_confidential_attachments()
            self.is_board_park = False

        except Exception as e:
            _logger.error("Error deleting articles: %s", str(e))
            raise ValidationError(f"An error occurred while deleting the articles: {str(e)}")

    def reload_func(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def remove_attendees_from_article(self):
        """
        Removes Board Members and Regular Attendees sections from the article.
        Provides success or failure notifications.
        """
        try:
            # Ensure an article exists
            if not self.article_id:
                raise UserError("No article found! Please create an article first.")

            # Parse the existing article body using BeautifulSoup
            existing_body = self.article_id.body
            soup = BeautifulSoup(existing_body, 'html.parser')

            # Find and remove sections with TO and CC headers
            to_section = soup.find('h3', string="TO:")
            cc_section = soup.find('h3', string="CC:")

            if to_section:
                # Remove the TO section (including its parent div and <hr>)
                to_div = to_section.find_parent('div')
                if to_div:
                    to_div.decompose()

            if cc_section:
                # Remove the CC section (including its parent div and <hr>)
                cc_div = cc_section.find_parent('div')
                if cc_div:
                    cc_div.decompose()

            # Update the article with the modified body
            new_body_content = str(soup)
            self.article_id.sudo().write({'body': Markup(new_body_content)})

            # Update timestamps
            self.last_write_date = fields.Datetime.now()
            self.last_write_count = 0  # Reset attendee count

            # Return a success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'All attendees have been successfully removed from the article!',
                    'type': 'success',  # 'success', 'warning', 'danger'
                    'sticky': False,  # Notification disappears after a few seconds
                }
            }

        except UserError as e:
            raise UserError(f"Error: {e}")

        except Exception as e:
            raise UserError(f"An unexpected error occurred: {e}")

    def create_article_calendar(self):
        if not self.product_line_ids:
            raise ValidationError("Please add an agenda before making an Article!")

        company_id = self.env.company
        logo_html = f'<img src="/web/image/res.company/{company_id.id}/logo" class="bg-view" alt="Company Logo"/>' if company_id.logo else ''

        def build_agenda_table(lines, is_confidential=False):
            html_content = """
                <table class="agenda-table table" style="width: 100%; table-layout: fixed; border: none; border-collapse: collapse;">
                    <colgroup style="border:none;">
                        <col style="width: 10%;" /> <!-- First column: 10% -->
                        <col style="width: 90%;" /> <!-- Second column: 90% -->
                    </colgroup>
                    <thead class="" display="none">
                        <tr>
                            <th style="padding: 10px; text-align: center; border: none;"></th>
                            <th style="padding: 10px; text-align: center; border: none;"></th>
                        </tr>
                    </thead>
                    <tbody id="article_body" style="border:none;">
            """
            for counter, line in enumerate(lines, start=1):
                presenters = ', '.join(presenter.name for presenter in line.presenter_id)
                description = "Confidential" if is_confidential and line.confidential else (line.description or '')
                html_content += f"""
                    <tr style="border: none;">
                        <td style="padding: 10px; border: none; text-align: center;">{counter}</td>
                        <td style="padding: 10px; border: none; text-align: justify;" class="text-justify">{description}</td>
                    </tr>
                """
            html_content += "</tbody></table>"
            return html_content

        original_agenda = build_agenda_table(self.product_line_ids)
        non_confidential_agenda = build_agenda_table(self.product_line_ids, is_confidential=True)

        def format_attendees_section(title, attendees):
            if not attendees:
                return ""

            section = f"""
            <div class="table-responsive my-3">
                <table class="table" style="table-layout: fixed; width: 100%; border: none; border-collapse: collapse;">
                    <colgroup>
                        <col style="width: 10%;" /> <!-- Title column -->
                        <col style="width: 5%;" />  <!-- Colon column -->
                        <col style="width: 85%;" /> <!-- Attendees column -->
                    </colgroup>
                    <thead class="" style="display:none;">
                        <tr style="border: none;">
                            <th style="border: none;"></th>
                            <th style="text-align: center; border: none;"></th>
                            <th style="border: none;"></th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for idx, attendee in enumerate(attendees):
                # Search for the employee linked to this partner
                employee = self.env['hr.employee'].sudo().search([('partner_id', '=', attendee.id)], limit=1)

                if not employee and attendee.email:
                    employee = self.env['hr.employee'].sudo().search([('work_email', '=', attendee.email)], limit=1)

                position = employee.job_id.name if employee and employee.job_id else "Unknown Position"

                section += f"""
                    <tr style="border: 1px 0px 0px 0px solid black;">
                        {"<td rowspan='{}' class='fw-bold' style='border: none;'>{}</td>".format(len(attendees), title) if idx == 0 else ""}
                        {"<td rowspan='{}' class='text-center' style='border: none;'>:</td>".format(len(attendees)) if idx == 0 else ""}
                        <td  style="border: none;">{attendee.name} <span class="text-muted">({position})</span></td>
                    </tr>
                """

            section += """
                    </tbody>
                </table>
            </div>
            """
            return section


        # Step 2: Separate attendees into board attendees and regular attendees
        board_attendees = [attendee for attendee in self.partner_ids if attendee.user_ids and any(
            user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_member')
            for user in attendee.user_ids if
            not user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_secretary')
        )]

        regular_attendees = [attendee for attendee in self.partner_ids if attendee not in board_attendees]

        if self.start:
            formatted_start_date = self.start.strftime('%d %B, %Y')
        else:
            formatted_start_date = ''

        shared_vars = {
            "logo_html": logo_html,
            "company_name": company_id.name,
            "company_street": company_id.street or '',
            "company_city": company_id.city or '',
            "company_country": company_id.country_id.name or '',
            "company_phone": company_id.phone or '',
            "company_email": company_id.email or '',
            "company_website": company_id.website or '',
            "event_name": self.name,
            "start_date": formatted_start_date,
            "organizer": self.user_id.name or '',
            "from":self.from_agenda,
        }

        description_content = f"""
            <div>
                <h3>Description</h3>
                <p>{Markup.escape(self.description)}</p>
                <hr/>
            </div>
        """ if self.description else ""

        base_content = """
            <div>
                <header style="text-align: center;">
                    {logo_html}<br><br>
                    <h2><strong>{company_name}</strong></h2>
                </header>
            <div class="container">
                <div class="card-body border-dark">
                    <table style="width: 100%; table-layout: fixed; border-collapse: collapse; border: none;">
                        <tr style="border: none;">
                            <!-- Left Column -->
                            <td style="text-align: left; vertical-align: top; border: none; padding: 0;">
                                <p class="mb-0"><span>{company_street}</span></p>
                                <p class="mb-0"><span>{company_city}</span></p>
                                <p class="mb-0"><span>{company_country}</span></p>
                            </td>
                            <!-- Right Column -->
                            <td style="text-align: right; vertical-align: top; border: none; padding: 0;">
                                <p class="mb-0"><span>{company_phone}</span></p>
                                <p class="mb-0"><span>{company_email}</span></p>
                                <p class="mb-0"><span>{company_website}</span></p>
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
                <br>
                <br>
                   <h3> <strong style="text-decoration:underline;"> CONFIDENTIAL </strong></h3>
                <br>
                <div class="container">
                    {description_content}
                    <div style="border-bottom:2px solid black"> 
                    {board_attendees_content}
                    </div
                    {regular_attendees_content}
                    <hr/>
                    <p> <strong> FROM:</strong> <span style="margin-left:0.5rem;"> {from} </span></p>
                    <p><strong>DATE:</strong> <span style="margin-left:0.5rem;">{start_date}</span></p>
                    <p><strong>SUBJECT:</strong><span style="margin-left:0.5rem;">{event_name}</span></p>
                    {agenda_content}
                    <p><strong></strong> {organizer}</p>
                </div>
            </div>
        """

        board_attendees_content = format_attendees_section("TO", board_attendees)
        regular_attendees_content = format_attendees_section("CC", regular_attendees)

        original_body = base_content.format(
            confidential_header="<h3 style='color: red; text-transform: uppercase;'>CONFIDENTIAL</h3>",
            description_content=description_content,
            board_attendees_content=board_attendees_content,
            regular_attendees_content=regular_attendees_content,
            agenda_content=original_agenda,
            **shared_vars
        )
        article = self.env['knowledge.article'].sudo().create({
            'name': f"Agenda: {self.name}",
            'body': original_body,
            'calendar_id': self.id,
        })
        self.article_id = article.id

        if self.has_confidential_agenda_item :
            non_confidential_body = base_content.format(
                confidential_header="",
                description_content=description_content,
                board_attendees_content=board_attendees_content,
                regular_attendees_content=regular_attendees_content,
                agenda_content=non_confidential_agenda,
                **shared_vars
            )
            non_conf_article = self.env['knowledge.article'].sudo().create({
                'name': f"Non-Confidential Agenda: {self.name}",
                'body': non_confidential_body,
                'calendar_id': self.id,
            })
            self.non_confidential_article_id = non_conf_article.id
        else:
            self.non_confidential_article_id = False

    def update_attendees_in_article(self):
        """
        Add Board Members and Regular Attendees sections above the Agenda header in an existing article.
        Provides success or failure notifications.
        """
        try:
            # Ensure an article is already created
            if not self.article_id:
                raise ValidationError("No article found! Please create an article first.")

            # Fetch attendees: Board members and regular attendees
            board_attendees = []
            regular_attendees = []

            for attendee in self.partner_ids:
                if attendee.is_board_member or attendee.is_board_secretary:
                    board_attendees.append(attendee)
                else:
                    regular_attendees.append(attendee)

            # Generate Board Members Section
            board_attendees_content = ""
            if board_attendees:
                board_attendees_content += "<div><h3>TO:</h3>"
                for attendee in board_attendees:
                    position = f" ({attendee.position})" if attendee.position else ""
                    board_attendees_content += f"<p>{attendee.attendee_name} {position}</p>"
                board_attendees_content += "</div><hr/>"

            # Generate Regular Attendees Section
            regular_attendees_content = ""
            if regular_attendees:
                regular_attendees_content += "<div><h3>CC:</h3>"
                for attendee in regular_attendees:
                    position = f" ({attendee.position})" if attendee.position else ""
                    regular_attendees_content += f"<p>{attendee.attendee_name} {position}</p>"
                regular_attendees_content += "</div><hr/>"

            # Combine both sections
            attendees_content = board_attendees_content + regular_attendees_content

            # Parse the existing article body using BeautifulSoup
            existing_body = self.article_id.body
            soup = BeautifulSoup(existing_body, 'html.parser')

            # Find the Agenda header
            agenda_header = soup.find('h3', string="Agenda")
            if agenda_header:
                # Insert attendees' content before the Agenda header
                attendees_soup = BeautifulSoup(attendees_content, 'html.parser')
                agenda_header.insert_before(attendees_soup)
            else:
                # Fallback: Append attendees' content at the end
                attendees_soup = BeautifulSoup(attendees_content, 'html.parser')
                soup.append(attendees_soup)

            # Update the article with the modified body
            new_body_content = str(soup)
            self.article_id.sudo().write({'body': Markup(new_body_content)})

            # Update timestamps
            self.last_write_date = fields.Datetime.now()
            self.last_write_count = len(self.attendees_lines_ids)

            # Return a success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Attendees successfully updated in the article!',
                    'type': 'success',  # 'success', 'warning', 'danger'
                    'sticky': False,  # Notification disappears after a few seconds
                }
            }

        except ValidationError as e:
            raise UserError(f"Error: {e}")

        except Exception as e:
            raise UserError(f"An unexpected error occurred: {e}")

    def update_agenda_lines(self):
        """
        Updates the agenda lines in the article body.
        Provides success or failure notifications.
        """
        try:
            # Check for product line ids
            if not self.product_line_ids:
                raise ValidationError("Please add an agenda before making an Article!")

            # Construct the HTML table
            html_content = Markup("""
                <table class="table">
                    <thead style="display:none">
                        <tr style="border: 0px; background-color: #ffffff;">
                            <th style="padding: 10px; border: 0px;">ID</th>
                            <th style="padding: 10px; border: 0px;">Agenda Item</th>
                            <th style="padding: 10px; border: 0px;">Presenter</th>
                        </tr>
                    </thead>
                    <tbody id="article_body">
            """)

            counter = 1
            for line in self.product_line_ids:
                presenters = ', '.join(presenter.name for presenter in line.presenter_id)
                html_content += Markup("""
                    <tr style="border: none;">
                        <td style="padding: 10px; border: 0px;">{counter}</td>
                        <td style="padding: 10px; border: 0px;">{description}</td>
                        <td style="padding: 10px; border: 0px;">{presenters}</td>
                    </tr>
                """).format(
                    counter=counter,
                    description=line.description or '',
                    presenters=presenters or ''
                )
                counter += 1

            html_content += Markup("</tbody></table>")

            # Get the existing article
            article = self.env['knowledge.article'].sudo().browse(self.article_id.id)

            # Update the article body
            body_content = article.body
            start_index = body_content.find('<h3>Agenda</h3>')
            end_index = body_content.find('</table>', start_index)

            if start_index == -1 or end_index == -1:
                raise ValidationError("Failed to update article: Agenda section not found.")

            body_content = body_content[:start_index + len('<h3>Agenda</h3>')] + html_content + body_content[
                                                                                                end_index + len(
                                                                                                    '</table>'):]

            # Update article body
            article.body = body_content
            self.last_write_count = len(self.product_line_ids)
            self.last_write_date = fields.Datetime.now()

            # Return a success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Agenda successfully updated in the article!',
                    'type': 'success',  # can be 'success', 'warning', or 'danger'
                    'sticky': False,  # Notification disappears after a few seconds
                }
            }

        except ValidationError as e:
            raise UserError(f"Error: {e}")

        except Exception as e:
            raise UserError(f"An unexpected error occurred: {e}")

    def cover_page_update(self):
        """
        Updates the cover page by:
        1. Removing existing attendees.
        2. Adding updated attendees.
        3. Updating agenda lines.
        Provides success or failure notifications.
        """
        try:
            # Step 1: Remove existing attendees
            self.remove_attendees_from_article()

            # Step 2: Add updated attendees
            self.update_attendees_in_article()

            # Step 3: Update agenda lines
            self.update_agenda_lines()

            # Update timestamps
            self.last_write_date = fields.Datetime.now()

            # Success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Cover page has been successfully updated!',
                    'type': 'success',  # Notification type
                    'sticky': False,  # Auto-dismiss notification
                }
            }

        except UserError as e:
            # Handle any known validation or user errors
            raise UserError(f"Error: {e}")

        except Exception as e:
            # Handle unexpected errors
            raise UserError(f"An unexpected error occurred: {e}")

    def action_add_knowledge_article(self):
        if not self.article_id:
            raise ValidationError("No Article for these records in Knowledge Module!")

        # Log initial conditions
        _logger.info("Starting action_add_knowledge_article")
        _logger.info(f"Article ID: {self.article_id.id}")
        _logger.info(f"Last write date: {self.last_write_date}")
        _logger.info(f"Product lines count: {len(self.product_line_ids)}")
        _logger.info(f"Attendees count: {len(self.attendees_lines_ids)}")

        # Ensure there's new data
        new_product_lines = [line for line in self.product_line_ids if line.create_date >= self.last_write_date]
        if not new_product_lines and not self.attendees_lines_ids:
            raise UserError(
                _("No new data added to the agenda or attendees! Please add data before making changes to the article!"))

        # Parse existing article content
        existing_content = self.article_id.body
        soup = BeautifulSoup(existing_content, 'html.parser')

        # Helper to find or raise for required headers
        def get_header(title):
            header = soup.find('h3', string=title)
            if not header:
                raise UserError(_(f"No '{title}' header found in the article!"))
            return header

        agenda_header = get_header("Agenda")

        # Extract current attendees from the article
        def extract_attendees_from_section(title):
            section_header = soup.find('h3', string=title)
            if not section_header:
                return []
            attendees = []
            for p in section_header.find_next_siblings('p'):
                if p.name == 'p':
                    attendees.append(p.get_text())
                else:
                    break
            return attendees

        existing_to_attendees = extract_attendees_from_section("TO:")
        existing_cc_attendees = extract_attendees_from_section("CC:")

        # Log extracted attendees
        _logger.info(f"Existing TO attendees: {existing_to_attendees}")
        _logger.info(f"Existing CC attendees: {existing_cc_attendees}")

        # Separate attendees into TO and CC
        to_attendees = [attendee for attendee in self.attendees_lines_ids if
                        attendee.is_board_member or attendee.is_board_secretary]
        cc_attendees = [attendee for attendee in self.attendees_lines_ids if
                        not attendee.is_board_member and not attendee.is_board_secretary]

        # Format new attendees for comparison
        def format_attendee(attendee):
            position = f" ({attendee.position})" if attendee.position else " (Unknown Position)"
            return f"{attendee.attendee_name}{position}"

        new_to_attendees = [format_attendee(attendee) for attendee in to_attendees]
        new_cc_attendees = [format_attendee(attendee) for attendee in cc_attendees]

        # Log new attendees
        _logger.info(f"New TO attendees: {new_to_attendees}")
        _logger.info(f"New CC attendees: {new_cc_attendees}")

        # Convert existing attendees to set for comparison (avoids duplicates)
        existing_to_set = set(existing_to_attendees)
        existing_cc_set = set(existing_cc_attendees)

        # Check if there are new attendees to add
        new_to_attendees_unique = [attendee for attendee in new_to_attendees if attendee not in existing_to_set]
        new_cc_attendees_unique = [attendee for attendee in new_cc_attendees if attendee not in existing_cc_set]

        # Log attendee comparison result
        _logger.info(f"New TO attendees (unique): {new_to_attendees_unique}")
        _logger.info(f"New CC attendees (unique): {new_cc_attendees_unique}")

        # Update attendees only if there are changes
        if new_to_attendees_unique or new_cc_attendees_unique:
            # Remove existing TO and CC sections
            _logger.info("Updating TO and CC sections.")
            for header in soup.find_all('h3', string=["TO:", "CC:"]):
                section = header.find_next_sibling('div')
                if section:
                    section.decompose()
                header.decompose()

            # Generate the TO and CC sections, adding only non-duplicate attendees
            def generate_attendee_section(title, attendees):
                section_html = f"<h3>{title}</h3>"
                if attendees:
                    for attendee in attendees:
                        section_html += f"<p>{attendee}</p>"
                else:
                    section_html += "<p>No attendees listed.</p>"
                return section_html

            to_section = generate_attendee_section("TO:", new_to_attendees_unique)
            cc_section = generate_attendee_section("CC:", new_cc_attendees_unique)

            # Insert the new TO and CC sections before the Agenda
            agenda_header.insert_before(BeautifulSoup(to_section, 'html.parser'))
            agenda_header.insert_before(BeautifulSoup(cc_section, 'html.parser'))

            _logger.info("Updated TO and CC sections successfully.")

        # Update the agenda table
        def update_agenda_table():
            table_body = soup.find('tbody')
            if not table_body:
                raise UserError(_("No tbody found in the agenda table!"))

            existing_serials = len([row for row in table_body.find_all('tr')])
            serial = existing_serials + 1

            for line in new_product_lines:
                presenters = ', '.join(presenter.name for presenter in line.presenter_id)
                description_soup = BeautifulSoup(line.description or '', 'html.parser')
                description_text = description_soup.get_text().replace('\n', '<br>')

                new_row = soup.new_tag('tr', style="border: 0px;")
                serial_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
                serial_td.string = str(serial)
                new_row.append(serial_td)

                description_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
                description_td.append(BeautifulSoup(description_text, 'html.parser'))
                new_row.append(description_td)

                presenters_td = soup.new_tag('td', style="padding: 10px; border: 0px;")
                presenters_td.string = presenters or ''
                new_row.append(presenters_td)

                table_body.append(new_row)
                serial += 1

            _logger.info("Updated agenda table successfully.")

        update_agenda_table()

        # Save changes back to the article
        self.last_write_date = fields.Datetime.now()
        updated_content = str(soup)

        # Log updated content
        _logger.info("Updated article content successfully.")
        self.article_id.sudo().write({'body': Markup(updated_content)})

    def action_delete_agenda_descriptions(self):
        try:
            # Unlink the original article if it exists
            if self.description_article_id:
                self.description_article_id.sudo().unlink()
                self.description_article_id = False

            # Unlink the alternate article if it exists
            if self.alternate_description_article_id:
                self.alternate_description_article_id.sudo().unlink()
                self.alternate_description_article_id = False

            # Reset the description creation flag
            self.is_description_created = False

            # Reload the view
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        except Exception as e:
            raise UserError(f"An error occurred while deleting the articles: {str(e)}")

    def action_create_agenda_descriptions(self):
        if not self.product_line_ids:
            raise ValidationError("Please add data before making an Article!")

        self.action_delete_agenda_descriptions()

        # Initialize attendee lists
        attendees_present = []
        attendees_in_attendance = []

        if not self.attendees_lines_ids:
            raise UserError(_('Kindly, add the attendees!'))

        # Classify attendees into two sections
        for attendee in self.attendees_lines_ids:
            if attendee.has_attended:
                if attendee.is_board_member and not attendee.is_board_secretary:
                    attendees_present.append(attendee)
                else:
                    attendees_in_attendance.append(attendee)

        # Generate the HTML for attendees
        def format_attendees_section(title, attendees):
            if not attendees:
                return ""
            section = f"""
            <div class="table-responsive my-3" style="border:none;">
                <table class="table" style="table-layout: fixed; width: 100%; border-bottom: 1px solid black; border-collapse: collapse;">
                    <colgroup style="border:none;">
                        <col style="width: 20%;" /> <!-- Title column -->
                        <col style="width: 5%;" />  <!-- Colon column -->
                        <col style="width: 75%;" /> <!-- Attendees column -->
                    </colgroup>
                    <tbody style="border:none;">
                        <tr style="border:none;">
                            <td rowspan="{len(attendees)}" class="fw-bold" style="border:none;">{title}</td>
                            <td rowspan="{len(attendees)}" class="text-center" style="border:none;">:</td>
                            <td style="border:none;">{attendees[0].attendee_name} <span class="text-muted" style="border:none">({attendees[0].position})</span></td>
                        </tr>
            """
            for attendee in attendees[1:]:
                section += f"""
                        <tr style="border:none;">
                            <td style="border:none">{attendee.attendee_name} <span class="text-muted" style="border:none">({attendee.position})</span></td>
                        </tr>
                """
            section += """
                    </tbody>
                </table>
            </div>
            """
            return section

        # Generate the sections
        section_present = format_attendees_section("PRESENT", attendees_present)
        section_in_attendance = format_attendees_section("IN ATTENDANCE", attendees_in_attendance)

        # Combine attendee sections
        attendees_section = section_present + section_in_attendance

        # Generate the table for product lines
        def build_minutes_table(lines, is_confidential=False):
            html_content = """
                <table class="agenda-table table" style="width: 100%; table-layout: fixed; border: none; border-collapse: collapse;">
                    <colgroup style="border:none;">
                        <col style="width: 10%;" /> <!-- First column: 10% -->
                        <col style="width: 90%;" /> <!-- Second column: 90% -->
                    </colgroup>
                    <tbody style="border:none;">
            """
            for counter, line in enumerate(lines, start=1):
                description = "Confidential" if is_confidential and line.confidential else (line.description or '')
                html_content += f"""
                    <tr style="border:none;">
                        <td style="padding: 10px; text-align: center; border:none;">{counter}</td>
                        <td style="padding: 10px; text-align: justify; border:none;">{description}</td>
                    </tr>
                """
            html_content += "</tbody></table>"
            return html_content

        # Create original and alternate minutes tables
        original_minutes_table = build_minutes_table(self.product_line_ids)
        alternate_minutes_table = build_minutes_table(self.product_line_ids, is_confidential=True)

        # Add company information
        company_id = self.env.company
        logo_html = f'<img src="/web/image/res.company/{company_id.id}/logo" class="bg-view" alt="Company Logo"/>' if company_id.logo else ''
        subject = self.name

        # Build the final body content
        # Build the final body content

        def build_body_content(subject, minutes_table):
            return f"""
                <div style="border:none;">
                    <header style="text-align: center; border:none;">
                        {logo_html}<br><br>
                        <h2><strong>{company_id.name}</strong></h2>
                    </header>
                    <br>
                    <h3><strong style="text-decoration:underline;">CONFIDENTIAL</strong></h3>
                    <h3><strong style="text-decoration:underline;">{subject}</strong></h3>
                    <hr style="border:none">
                    {attendees_section}
                    {minutes_table}
                </div>
            """

        # Create the articles
        original_body_content = build_body_content(subject, original_minutes_table)
        alternate_body_content = build_body_content(subject, alternate_minutes_table)  # Pass as two arguments

        # Create original article
        original_article_values = {
            'name': f"Minutes: {self.name}",
            'body': original_body_content,
            'calendar_id': self.id,
        }
        original_article = self.env['knowledge.article'].sudo().create(original_article_values)
        self.description_article_id = original_article
        if self.has_confidential_agenda_item:
            alternate_article_values = {
                'name': f"Minutes: {self.name} (Non-Confidential)",
                'body': alternate_body_content,
                'calendar_id': self.id,
            }
            alternate_article = self.env['knowledge.article'].sudo().create(alternate_article_values)
            self.alternate_description_article_id = alternate_article
        else:
            self.alternate_description_article_id = False

        self.is_description_created = True
        self.is_minutes_created = True
        # return self.action_view_description_article()

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

    def action_non_confidential_view_knowledge_article(self):

        self.ensure_one()
        for record in self:
            if record.non_confidential_article_id:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Knowledge Article',
                    'res_model': 'knowledge.article',
                    'view_mode': 'form',
                    'res_id': record.non_confidential_article_id.id,
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

    def action_view_alternate_description_article(self):
        self.ensure_one()
        if self.alternate_description_article_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Knowledge Article',
                'res_model': 'knowledge.article',
                'view_mode': 'form',
                'res_id': self.alternate_description_article_id.id,
                'target': 'current',
            }

    def action_open_documents_minutes(self):
        self.ensure_one()
        upload_type = self.env.context.get('upload_type')
        confidential = self.env.context.get('default_confidential', False)

        # Fetch board members and secretaries if confidential is True
        restricted_partners = []
        if confidential:
            board_member_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_member')
            board_secretary_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_secretary')

            restricted_users = self.env['res.users'].search([
                ('groups_id', 'in', [board_member_group.id, board_secretary_group.id])
            ])
            restricted_partners = restricted_users.mapped('partner_id').ids

        return {
            'type': 'ir.actions.act_window',
            'name': 'Minutes Upload',
            'res_model': 'calendar.event.minutes.line',
            'view_mode': 'form',
            'view_id': self.env.ref('odoo_calendar_inheritence.calendar_event_product_line_form_view_minutes').id,
            'target': 'new',
            'context': {
                'default_calendar_id': self.id,
                'default_confidential': confidential,
                'upload_type': upload_type,
                'default_Restricted': [(6, 0, restricted_partners)],  # Set default Restricted users
            },
        }

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

    @api.depends('minutes_line_ids')
    def _compute_minutes_documents(self):
        for event in self:
            product_ids = event.minutes_line_ids.mapped('product_id')
            print(f"Computing product documents for event {event.id}, product_ids: {product_ids.ids}")
            if product_ids:
                documents = self.env['product.document'].search([('product_id', 'in', product_ids.ids)])
                print(f"Found documents: {documents.ids} for product_ids: {product_ids.ids}")
                event.minutes_document_ids = [(6, 0, documents.ids)]
            else:
                event.minutes_document_ids = [(5,)]  # Clear if no products
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
            rec.is_minutes_created = False
            rec.is_minutes_published = False
            rec.is_confidential_minutes_uploaded = False
            rec.is_non_confidential_minutes_uploaded = False
            rec.is_minutes_uploaded = False
            self.env['calendar.event.minutes.line'].delete_all_for_calendar_event(rec.id)
            rec.action_delete_minutes_documents()
            rec.description_article_id.sudo().unlink()
            rec.action_delete_agenda_descriptions()

    def action_add_attendees(self):
        partners = []
        for partner in self.partner_ids:
            employee = self.env['hr.employee'].sudo().search([('partner_id', '=', partner.id)], limit=1)
            _logger.info(
                f"Checking partner {partner.name} - Found Employee: {employee.name if employee else 'None'}")

            if not employee and partner.email:
                employee = self.env['hr.employee'].search(
                    [('work_email', '=', partner.email)],
                    limit=1
                )
            if employee:
                position = employee.job_id.name if employee.job_id else 'Unknown Position'
            else:
                position = 'Unknown Position'


                # Debugging output
            _logger.info(
                f"Partner: {partner.name}, Employee: {employee.name if employee else 'None'}, Position: {position}")

            _logger.info("Attendee: %s, Position: %s", partner.name, position)
            user = self.env['res.users'].search([('partner_id', '=', partner.id)], limit=1)
            if user:
                is_board_member = user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_member')
                is_board_secretary = user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_secretary')

                if is_board_member or is_board_secretary:
                    role = 'Board Member' if is_board_member else 'Board Secretary'
                    _logger.info("Attendee %s is a %s", partner.name, role)
                else:
                    _logger.info("Attendee %s does not belong to any board-related group", partner.name)

            partners.append(
                Command.create(
                    {
                        'attendee_name': partner.name,
                        'email': partner.email,
                        'phone': partner.phone,
                        'position': position,
                        'is_board_member': is_board_member if user else False,
                        'is_board_secretary': is_board_secretary if user else False,
                    }
                )
            )

        # Update the attendees list
        if not self.attendees_lines_ids:
            self.attendees_lines_ids = partners
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

    def action_open_boardpack(self):
        self.ensure_one()

        # Fetch attachments using prefix-based names
        confidential_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            ('name', 'ilike', f"Boardpack_Confidential_{self.name}.pdf")
        ], limit=1)

        non_confidential_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            ('name', 'ilike', f"Boardpack_NonConfidential_{self.name}.pdf")
        ], limit=1)

        accessible_attachment_ids = []
        if non_confidential_attachment:
            accessible_attachment_ids.append(non_confidential_attachment.id)
        if confidential_attachment:
            accessible_attachment_ids.append(confidential_attachment.id)

        if not accessible_attachment_ids:
            return {'type': 'ir.actions.act_window_close'}

        matching_documents = self.env['product.document'].search(
            [('ir_attachment_id', 'in', accessible_attachment_ids)]
        )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'product.document',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', matching_documents.ids), ('partner_ids', 'in', [self.env.user.partner_id.id])],
            'context': {'default_res_model': 'calendar.event', 'default_res_id': self.id},
        }

    def action_open_minutes(self):
        self.ensure_one()

        # Fetch Confidential and Non-Confidential boardpacks directly linked to the event
        confidential_attachment_id = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            ('name', 'ilike', f"Minutes_Confidential_{self.name}.pdf")
        ], limit=1)

        non_confidential_attachment_id = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            ('name', 'ilike', f"Minutes_NonConfidential_{self.name}.pdf")
        ], limit=1)

        # Determine accessible files from the main event
        accessible_attachment_ids = []
        if non_confidential_attachment_id:
            accessible_attachment_ids.append(non_confidential_attachment_id.id)
        if confidential_attachment_id:
            accessible_attachment_ids.append(confidential_attachment_id.id)

        # Fetch uploaded attachments from related minutes lines
        minutes_lines = self.env['calendar.event.minutes.line'].search([('calendar_id', '=', self.id)])
        uploaded_attachment_ids = minutes_lines.mapped('pdf_attachment').ids


        # Combine attachments from both sources
        all_accessible_attachment_ids = list(set(accessible_attachment_ids + uploaded_attachment_ids))

        # Log accessible attachments
        _logger.info("User %s is accessing the following attachments: %s",
                     self.env.user.name, all_accessible_attachment_ids)

        # Check if no files are accessible
        if not all_accessible_attachment_ids:
            _logger.info("No accessible attachments for user %s on event %s", self.env.user.name, self.name)
            return {'type': 'ir.actions.act_window_close'}

        # Fetch matching product documents
        matching_documents = self.env['product.document'].search(
            [('ir_attachment_id', 'in', all_accessible_attachment_ids)])
        _logger.info("Matching Product Document count for user %s: %d", self.env.user.name, len(matching_documents))

        # Log retrieved document names
        _logger.info("User %s retrieved the following documents: %s", self.env.user.name,
                     matching_documents.mapped('name'))

        # Get active user partner ID
        active_user = self.env.user.partner_id.id

        # Return action to open documents
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'product.document',
            'view_mode': 'kanban,tree,form',
            'domain': [
                '&',
                ('id', 'in', matching_documents.ids),
                ('partner_ids', 'in', [active_user])
            ],
            'context': {'default_res_model': 'calendar.event', 'default_res_id': self.id},
        }

    def action_open_documents(self):
        self.ensure_one()
        confidential_attachment_ids = []
        non_confidential_attachment_ids = []

        # Fetch attachments for board packs and minutes
        for suffix in ["Boardpack_Confidential", "Boardpack_NonConfidential", "Minutes_Confidential",
                       "Minutes_NonConfidential"]:
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'calendar.event'),
                ('res_id', '=', self.id),
                ('name', 'ilike', f"{suffix}_{self.name}.pdf")
            ], limit=1)
            if attachment:
                if "Confidential" in suffix:
                    confidential_attachment_ids.append(attachment.id)
                else:
                    non_confidential_attachment_ids.append(attachment.id)
            else:
                _logger.info(f"No attachment found for {suffix} file for event {self.name}")

        # Fetch unrestricted attachments from product_line_ids
        unrestricted_attachment_ids = [
            att.id for line in self.product_line_ids if not line.is_user_restricted for att in line.pdf_attachment
        ]

        # Fetch unrestricted attachments from minutes_line_ids
        minutes_attachment_ids = [
            att.id for line in self.minutes_line_ids if not line.is_user_restricted for att in line.pdf_attachment
        ]

        # Fetch unrestricted attachments from calendar_minutes_event_line
        minutes_event_attachment_ids = [
            att.id for line in self.minutes_line_ids if not line.is_user_restricted for att in line.pdf_attachment
        ]

        # Check if user is Board Member or Board Secretary
        is_board_member_or_secretary = self.env.user.has_group(
            'odoo_calendar_inheritence.group_agenda_meeting_board_member') or \
                                       self.env.user.has_group(
                                           'odoo_calendar_inheritence.group_agenda_meeting_board_secretary')

        # Combine all accessible files
        all_attachment_ids = (
                unrestricted_attachment_ids +
                minutes_attachment_ids +
                minutes_event_attachment_ids +
                non_confidential_attachment_ids
        )

        if is_board_member_or_secretary:
            all_attachment_ids += confidential_attachment_ids

        # Log accessible attachments
        _logger.info("User %s is accessing the following attachments: %s", self.env.user.name, all_attachment_ids)

        # Check if no files are found
        if not all_attachment_ids:
            _logger.info("No accessible attachments for user %s on event %s", self.env.user.name, self.name)
            return {'type': 'ir.actions.act_window_close'}

        # Fetch matching product documents
        matching_documents = self.env['product.document'].search([('ir_attachment_id', 'in', all_attachment_ids)])
        _logger.info("Matching Product Document count for user %s: %d", self.env.user.name, len(matching_documents))
        _logger.info("User %s retrieved the following documents: %s", self.env.user.name,
                     matching_documents.mapped('name'))

        active_user = self.env.user.partner_id.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'product.document',
            'view_mode': 'kanban,tree,form',
            'domain': [
                '&',
                ('id', 'in', matching_documents.ids),
                ('partner_ids', 'in', [active_user])
            ],
            'context': {'default_res_model': 'calendar.event', 'default_res_id': self.id},
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
    def compute_visible_users(self, product_document_ids=None):
        for record in self:
            if record.product_id and record.partner_ids:
                # Determine which product documents to update
                target_documents = product_document_ids or record.product_id.product_document_ids
                # Prepare partner names and document names for logging
                partner_names = ", ".join(record.partner_ids.mapped('name'))
                # Perform the update
                target_documents.sudo().write({
                    'partner_ids': [(6, 0, record.partner_ids.ids)]
                })

    def action_agenda_inv_sendmail(self):
        email = self.env.user.email
        if email:
            for meeting in self:
                meeting.attendee_ids._send_custom_mail_to_attendees(
                    self.env.ref('odoo_calendar_inheritence.calendar_template_agenda_meeting_invitation',
                                 raise_if_not_found=False)
                )
        return True

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

    def save_merged_document(self, pdf_stream, filename_prefix, description):
        """
        Save a single PDF document to `ir.attachment` and associate it with `product.document`.
        """
        self.ensure_one()

        # Reset the stream pointer before reading
        if pdf_stream.seekable():
            pdf_stream.seek(0)

        filename = f"{filename_prefix}.pdf"
        _logger.info("Processing file: %s", filename)

        # Log all invitees for the calendar event
        invitees = self.partner_ids
        _logger.info("Invitees for calendar.event '%s': %s", self.name, [partner.name for partner in invitees])

        # Determine the confidentiality status
        is_confidential = "NonConfidential" not in filename_prefix
        _logger.info("File confidentiality status: %s", "Confidential" if is_confidential else "Non-confidential")

        # Define groups for board members and board secretaries
        board_member_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_member')
        board_secretary_group = self.env.ref('odoo_calendar_inheritence.group_agenda_meeting_board_secretary')

        # Fetch partners dynamically based on groups
        board_partners = self.env['res.partner'].search([
            ('user_ids.groups_id', 'in', board_member_group.id)
        ]) | self.env['res.partner'].search([
            ('user_ids.groups_id', 'in', board_secretary_group.id)
        ])

        # Correct invitee logic
        # partners_to_add = invitees.ids if is_confidential else board_partners.ids
        partners_to_add = board_partners.ids if is_confidential else invitees.ids
        _logger.info("Adding partners for %s file. Partner IDs: %s",
                     "confidential" if is_confidential else "non-confidential", partners_to_add)

        # Search for existing attachments
        existing_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            ('name', '=', filename),
        ], limit=1)

        if existing_attachment:
            existing_attachment.unlink()
            _logger.info("Existing attachment '%s' removed.", filename)

        # Create new attachment
        attachment_env = self.env['ir.attachment'].with_context(skip_watermark=True)
        merged_attachment = attachment_env.create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_stream.read()),
            'mimetype': 'application/pdf',
            'res_model': 'calendar.event',
            'res_id': self.id,
        })

        _logger.info("New attachment created: %s with ID: %d", merged_attachment.name, merged_attachment.id)

        # Create or update `product.document`
        product_document = self.env['product.document'].search([('ir_attachment_id', '=', merged_attachment.id)],
                                                               limit=1)
        if not product_document:
            product_document = self.env['product.document'].create({
                'name': merged_attachment.name,
                'ir_attachment_id': merged_attachment.id,
                'description': description,
                'partner_ids': [(6, 0, partners_to_add)],
            })
            _logger.info("New product.document created for attachment: %s with partners: %s",
                         merged_attachment.name, partners_to_add)
        else:
            # Merge existing partners with the new ones
            current_partner_ids = product_document.partner_ids.ids
            new_partner_ids = current_partner_ids + partners_to_add
            product_document.write({
                'name': merged_attachment.name,
                'description': description,
                'partner_ids': [(6, 0, list(set(new_partner_ids)))]
            })
            _logger.info("Updated product.document for attachment: %s with merged partners: %s",
                         merged_attachment.name, list(set(new_partner_ids)))

        return merged_attachment

    def remove_confidential_attachments(self):
        """
        Check and remove existing attachments for the `calendar.event`
        with filenames containing `_NonConfidential` or `_Confidential`.
        """
        self.ensure_one()

        # Search for attachments with the specified prefixes
        domain = [
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            '|',
            ('name', 'ilike', 'Boardpack_NonConfidential'),
            ('name', 'ilike', 'Boardpack_Confidential'),
        ]

        existing_attachments = self.env['ir.attachment'].search(domain)

        if existing_attachments:
            # Log the names of attachments being removed
            for attachment in existing_attachments:
                _logger.info("Removing existing attachment: %s", attachment.name)

            # Remove the attachments
            existing_attachments.unlink()
            _logger.info("Removed %d attachment(s) for calendar.event '%s'.", len(existing_attachments), self.name)
        else:
            _logger.info("No confidential or non-confidential attachments found for calendar.event '%s'.", self.name)

    def _classify_attachments(self):
        """
        Classify attachments into confidential and non-confidential based on product lines.
        """
        confidential_attachments = []
        non_confidential_attachments = []

        for line in self.product_line_ids:
            if line.confidential:
                confidential_attachments.extend(line.pdf_attachment)
            else:
                non_confidential_attachments.extend(line.pdf_attachment)

        return confidential_attachments, non_confidential_attachments

    def _merge_attachments(self, cover_file_path, attachments):
        """
        Merge the cover file (from disk) with provided attachments.
        """
        from PyPDF2 import PdfWriter, PdfReader
        from io import BytesIO
        import base64

        self.ensure_one()
        merged_stream = BytesIO()  # Initialize in-memory buffer for the final merged PDF
        pdf_writer = PdfWriter()
        pdf_writer.compress_content = False  # Ensure no compression is applied

        # Add all pages of the cover file
        try:
            cover_reader = PdfReader(cover_file_path)
            for page in cover_reader.pages:
                pdf_writer.add_page(page)
        except Exception as e:
            _logger.error(f"Error reading cover file at {cover_file_path}: {e}")
            raise UserError(_("Failed to read the cover file: %s") % cover_file_path)

        # Process and add attachments
        for attachment in attachments:
            try:
                attachment_data = base64.b64decode(attachment.datas)
                attachment_reader = PdfReader(BytesIO(attachment_data))

                for page in attachment_reader.pages:
                    pdf_writer.add_page(page)
            except Exception as e:
                _logger.error(f"Error processing attachment: {e}")
                raise UserError(_("Failed to process an attachment."))

        # Write the final merged PDF to the in-memory buffer
        pdf_writer.write(merged_stream)
        merged_stream.seek(0)
        return merged_stream

    def _generate_cover_html(self, company_logo_base64, article_body, is_confidential=True):
        """
        Generate HTML content for the cover page, save as both HTML and PDF.
        """
        if not article_body:
            raise UserError(_("No article body found to generate the cover page."))

        html_content = article_body

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        html_content = html_content.replace('/web/image', f'{base_url}/web/image')

        bootstrap_url = f'{base_url}/odoo_calendar_inheritence/static/src/bootstrap-5.1.3/css/bootstrap.min.css'
        bootstrap_css = f'<link rel="stylesheet" href="{bootstrap_url}">'

        html_content_with_logo = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                {bootstrap_css}
                <style>
                    .page-break {{ 
                        page-break-before: always; 
                        margin-top: 10mm;
                    }}
                </style>
            </head>
            <body>
        """
        if company_logo_base64:
            html_content_with_logo += """
                <div style="text-align: center; margin-bottom: 20px;">
                    <img src="data:image/png;base64,[LOGO OMITTED]">
                </div>
            """

        # Add content and page breaks
        html_content_with_logo += f"""
            <div>
                <div class="content-section">
                    {html_content}
                </div>
            </div>
            </body>
            </html>
        """

        # Define file names
        doc_type = 'confidential' if is_confidential else 'non_confidential'
        html_file_path = f'/opt/{doc_type}_cover.html'
        pdf_file_path = f'/opt/{doc_type}_cover.pdf'

        # Save HTML file
        try:
            with open(html_file_path, 'w', encoding='utf-8') as html_file:
                html_file.write(html_content_with_logo)
            _logger.info(f"HTML file successfully saved at: {html_file_path}")
        except Exception as e:
            _logger.error(f"Failed to save HTML file: {e}")
            raise UserError(_("Failed to save HTML file."))

        # Convert HTML to PDF using wkhtmltopdf
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_html_file:
                tmp_html_file.write(html_content_with_logo.encode('utf-8'))
                tmp_html_path = tmp_html_file.name

            command = ['wkhtmltopdf', tmp_html_path, pdf_file_path]
            subprocess.run(command, check=True)
            _logger.info(f"PDF file successfully saved at: {pdf_file_path}")
        except subprocess.CalledProcessError as e:
            _logger.error(f"Failed to generate or save PDF file: {e}")
            # raise UserError(_("Failed to generate or save PDF file."))
        finally:
            # Clean up temporary HTML file
            if tmp_html_path:
                try:
                    os.unlink(tmp_html_path)
                except OSError:
                    pass

        return html_content_with_logo

    def _generate_minutes_cover_html(self, company_logo_base64, article_body, is_confidential=True):
        """
        Generate HTML content for the cover page, save as both HTML and PDF.
        """
        if not article_body:
            raise UserError(_("No article body found to generate the cover page."))

        html_content = article_body

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        html_content = html_content.replace('/web/image', f'{base_url}/web/image')

        bootstrap_url = f'{base_url}/odoo_calendar_inheritence/static/src/bootstrap-5.1.3/css/bootstrap.min.css'
        bootstrap_css = f'<link rel="stylesheet" href="{bootstrap_url}">'

        html_content_with_logo = f"""
               <!DOCTYPE html>
               <html lang="en">
               <head>
                   <meta charset="UTF-8">
                   <meta name="viewport" content="width=device-width, initial-scale=1.0">
                   {bootstrap_css}
                   <style>
                       .page-break {{ 
                           page-break-before: always; 
                           margin-top: 10mm;
                       }}
                   </style>
               </head>
               <body>
           """
        if company_logo_base64:
            html_content_with_logo += """
                   <div style="text-align: center; margin-bottom: 20px;">
                       <img src="data:image/png;base64,[LOGO OMITTED]">
                   </div>
               """

        # Add content and page breaks
        html_content_with_logo += f"""
               <div>
                   <div class="content-section">
                       {html_content}
                   </div>
               </div>
               </body>
               </html>
           """

        # Define file names
        doc_type = 'confidential' if is_confidential else 'non_confidential'
        html_file_path = f'/opt/{doc_type}_minutes_cover.html'
        pdf_file_path = f'/opt/{doc_type}_minutes_cover.pdf'

        # Save HTML file
        try:
            with open(html_file_path, 'w', encoding='utf-8') as html_file:
                html_file.write(html_content_with_logo)
            _logger.info(f"HTML file successfully saved at: {html_file_path}")
        except Exception as e:
            _logger.error(f"Failed to save HTML file: {e}")
            raise UserError(_("Failed to save HTML file."))

        # Convert HTML to PDF using wkhtmltopdf
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_html_file:
                tmp_html_file.write(html_content_with_logo.encode('utf-8'))
                tmp_html_path = tmp_html_file.name

            command = ['wkhtmltopdf', tmp_html_path, pdf_file_path]
            subprocess.run(command, check=True)
            _logger.info(f"PDF file successfully saved at: {pdf_file_path}")
        except subprocess.CalledProcessError as e:
            _logger.error(f"Failed to generate or save PDF file: {e}")
            # raise UserError(_("Failed to generate or save PDF file."))
        finally:
            # Clean up temporary HTML file
            if tmp_html_path:
                try:
                    os.unlink(tmp_html_path)
                except OSError:
                    pass

        return html_content_with_logo

    def _get_company_logo_base64(self):
        """
        Fetch the company logo and return it as a Base64-encoded string.
        """
        company = self.env.company
        if company.logo:
            return base64.b64encode(company.logo).decode('utf-8')
        else:
            return None

    def action_merge_documents(self):
        """
        Merge attachments into two distinct documents:
        Confidential (all attachments) and Non-Confidential (excluding confidential attachments).
        """
        self.ensure_one()

        # Generate the confidential and non-confidential cover HTML and save as PDFs
        company_logo_base64 = self.env.company.logo or None
        confidential_article_body = self.article_id.body if self.article_id else None
        non_conf_article_body = self.non_confidential_article_id.body if self.non_confidential_article_id else None

        if not confidential_article_body:
            raise UserError(_("No article found for confidential cover page."))

        # Generate confidential cover page
        self._generate_cover_html(company_logo_base64, confidential_article_body, is_confidential=True)
        confidential_cover_path = '/opt/confidential_cover.pdf'

        # Generate non-confidential cover page if applicable
        non_confidential_cover_path = None
        if non_conf_article_body:
            self._generate_cover_html(company_logo_base64, non_conf_article_body, is_confidential=False)
            non_confidential_cover_path = '/opt/non_confidential_cover.pdf'

        # Classify attachments
        confidential_attachments, non_confidential_attachments = self._classify_attachments()

        saved_documents = {}

        # For Confidential: Merge cover page with all attachments
        if confidential_attachments or non_confidential_attachments or not (
                confidential_attachments and non_confidential_attachments):
            confidential_stream = self._merge_attachments(
                confidential_cover_path, confidential_attachments + non_confidential_attachments
            )
            saved_documents["Confidential"] = self.save_merged_document(
                confidential_stream,
                filename_prefix=f"Boardpack_Confidential_{self.name}",
                description=f"Confidential document for event {self.name}"
            )

        # For Non-Confidential: Merge cover page with only non-confidential attachments
        if non_confidential_cover_path:
            if non_confidential_attachments:
                non_confidential_stream = self._merge_attachments(
                    non_confidential_cover_path, non_confidential_attachments
                )
            else:
                non_confidential_stream = open(non_confidential_cover_path, 'rb')

            saved_documents["NonConfidential"] = self.save_merged_document(
                non_confidential_stream,
                filename_prefix=f"Boardpack_NonConfidential_{self.name}",
                description=f"Non-confidential document for event {self.name}"
            )

        # Log details of saved documents
        _logger.info("Number of files saved: %d", len(saved_documents))
        for doc_type, attachment in saved_documents.items():
            if attachment:
                _logger.info("Saved document: %s (Type: %s)", attachment.name, doc_type)
            else:
                _logger.warning("No document saved for type: %s", doc_type)
        self.is_board_park = True
        action = self.action_open_boardpack()
        return action

    def action_merge_minutes_documents(self):
        """
        Generate and save cover pages for meeting minutes (Confidential and Non-Confidential),
        without merging any attachments.
        """
        self.ensure_one()

        # Generate the confidential and non-confidential cover HTML and save as PDFs
        company_logo_base64 = self.env.company.logo or None
        confidential_minutes_article_body = self.description_article_id.body if self.description_article_id else None

        non_conf_minutes_article = self.env['knowledge.article'].search(
            [('id', '=', self.alternate_description_article_id.id)], limit=1)
        non_conf_minutes_article_body = non_conf_minutes_article.body if non_conf_minutes_article else None

        if not confidential_minutes_article_body:
            raise UserError(_("No article found for confidential minutes cover page."))

        # Generate confidential cover page
        self._generate_minutes_cover_html(company_logo_base64, confidential_minutes_article_body, is_confidential=True)
        confidential_cover_path = '/opt/confidential_minutes_cover.pdf'

        # Generate non-confidential cover page if non_conf_minutes_article_body exists
        non_confidential_cover_path = None
        if non_conf_minutes_article_body:
            self._generate_minutes_cover_html(company_logo_base64, non_conf_minutes_article_body, is_confidential=False)
            non_confidential_cover_path = '/opt/non_confidential_minutes_cover.pdf'

        saved_documents = {}

        # Save the confidential cover page
        with open(confidential_cover_path, 'rb') as confidential_stream:
            saved_documents["Confidential"] = self.save_merged_document(
                confidential_stream,
                filename_prefix=f"Minutes_Confidential_{self.name}",
                description=f"Confidential minutes for event {self.name}"
            )

        # Save the non-confidential cover page if it exists
        if non_confidential_cover_path:
            with open(non_confidential_cover_path, 'rb') as non_confidential_stream:
                saved_documents["NonConfidential"] = self.save_merged_document(
                    non_confidential_stream,
                    filename_prefix=f"Minutes_NonConfidential_{self.name}",
                    description=f"Non-confidential minutes for event {self.name}"
                )

        # Log details of saved documents
        _logger.info("Number of minutes files saved: %d", len(saved_documents))
        for doc_type, attachment in saved_documents.items():
            if attachment:
                _logger.info("Saved minutes document: %s (Type: %s)", attachment.name, doc_type)
            else:
                _logger.warning("No document saved for type: %s", doc_type)

        # Explicitly return the action or any additional UI updates as needed
        self.is_minutes_published = True
        return self.action_open_minutes()

    def action_delete_minutes_documents(self):
        """
        Delete the saved confidential and non-confidential minutes documents
        related to this calendar event.
        """
        self.ensure_one()

        # Define the expected file name suffixes
        filename_suffixes = [f"Minutes_Confidential_{self.name}.pdf", f"Minutes_NonConfidential_{self.name}.pdf"]

        # Search for matching attachments
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            ('name', 'ilike', self.name)
        ])

        # Filter attachments that match the expected filename patterns
        attachments_to_delete = attachments.filtered(
            lambda att: any(suffix in att.name for suffix in filename_suffixes))

        if attachments_to_delete:
            attachments_to_delete.unlink()
            _logger.info("Deleted minutes documents for event: %s", self.name)
        else:
            _logger.warning("No minutes documents found for deletion for event: %s", self.name)

        # Delete related product.document records
        product_documents = self.env['product.document'].search([
            ('ir_attachment_id', 'in', attachments_to_delete.ids)
        ])

        if product_documents:
            product_documents.unlink()
            _logger.info("Deleted product.document records linked to minutes for event: %s", self.name)
        else:
            _logger.warning("No product.document records found for deletion for event: %s", self.name)

        return True


class AgendaLines(models.Model):
    _name = 'agenda.lines'
    _description = 'Agenda Lines'

    calendar_id = fields.Many2one('calendar.event', string="Calendar")
    description = fields.Html(related='calendar_id.agenda_description')
    partner_ids = fields.Many2many('res.partner', string='Attendees')
    duration = fields.Float(related="calendar_id.duration", string='Duration')
    agenda_attachment_ids = fields.Many2many(comodel_name='ir.attachment', string="Attachments")



