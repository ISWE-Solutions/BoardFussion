from email.policy import default

from PyPDF2 import PdfReader, PdfWriter
import re
from markupsafe import Markup
from bs4 import BeautifulSoup
from io import BytesIO
import base64
import zipfile
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
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, ListFlowable, ListItem
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.units import inch
from io import StringIO, BytesIO
from xml.sax.saxutils import escape
from weasyprint import HTML
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from io import BytesIO
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
    alternate_description_article_id = fields.Many2one('knowledge.article',
                                                       string='Related NON-confidential Description Article')
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
    is_minutes_created = fields.Boolean(string="Are minutes Generated")
    is_minutes_published = fields.Boolean(string="Are minutes published")
    is_minutes_uploaded = fields.Boolean(string="Are minutes Uploaded")
    is_boardpack_created = fields.Boolean(string="Are Boardpacks Generated")
    create_text = fields.Char(string="true or false", default="False")

    is_confidential_minutes_uploaded = fields.Boolean(default=False)
    is_non_confidential_minutes_uploaded = fields.Boolean(default=False)

    user_is_board_secretary = fields.Boolean(compute='_compute_user_is_board_secretary')

    @api.depends_context('uid')
    def _compute_user_is_board_secretary(self):
        for event in self:
            event.user_is_board_secretary = self.env.user.has_group(
                'odoo_calendar_inheritence.group_agenda_meeting_board_secretary')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(OdooCalendarInheritence, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                   toolbar=toolbar,
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
        if 'name' in vals and self.project_id:
            self.project_id.sudo().write({'name': vals['name']})
        # Disable email notifications by setting 'dont_notify' in context.
        res = super(OdooCalendarInheritence, self.with_context(dont_notify=True)).write(vals)
        return res

    @api.depends('article_id')
    def _compute_article_exists(self):
        for record in self:
            record.article_exists = bool(record.article_id)

    @api.depends('non_confidential_article_id')
    def _compute_article_non_exists(self):
        for record in self:
            record.article_non_exists = bool(record.non_confidential_article_id)

    # def _get_src_data_b64(self, value):
    #     try:  # FIXME: maaaaaybe it could also take raw bytes?
    #         image = Image.open(BytesIO(base64.b64decode(value)))
    #         image.verify()
    #
    #     except IOError:
    #         raise ValueError("Non-image binary fields can not be converted to HTML")
    #     except:  # image.verify() throws "suitable exceptions", I have no idea what they are
    #         raise ValueError("Invalid image content")
    #
    #     return "data:%s;base64,%s" % (Image.MIME[image.format], value.decode('ascii'))

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

        non_secretary_attendees = [
            attendee for attendee in self.partner_ids
            if not any(user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_secretary')
                       for user in attendee.user_ids)
        ]

        # From the non-secretary attendees, build the board attendees list
        board_attendees = [
            attendee for attendee in non_secretary_attendees
            if attendee.user_ids and any(
                user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_member')
                for user in attendee.user_ids
            )
        ]

        # Regular attendees are those that are in the non_secretary_attendees but not in board_attendees
        regular_attendees = [
            attendee for attendee in non_secretary_attendees
            if attendee not in board_attendees
        ]

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
            "from": self.from_agenda,
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
                    <div style="padding:1rem;"> 
                    {board_attendees_content}
                    </div>
                    <div style="padding:1rem;">
                    {regular_attendees_content}
                    </div>
                    <hr/>
                    <p> <strong> FROM:</strong> <span style="margin-left:0.5rem;"> {from} </span></p>
                    <p><strong>DATE:</strong> <span style="margin-left:0.5rem;">{start_date}</span></p>
                    <p><strong>SUBJECT:</strong><span style="margin-left:0.5rem;">{event_name}</span></p>
                    {agenda_content}
                    <p><strong></strong> {from}</p>
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

        if self.has_confidential_agenda_item:
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
                # Skip board secretaries entirely
                if attendee.is_board_secretary:
                    continue
                # Add board members (who are not secretaries) to PRESENT
                if attendee.is_board_member:
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
                        <tr style="border:none; padding:1rem;">
                            <td rowspan="{len(attendees)}" class="fw-bold" style="border:none;">{title}</td>
                            <td rowspan="{len(attendees)}" class="text-center" style="border:none;">:</td>
                            <td style="border:none;">{attendees[0].attendee_name} <span class="text-muted" style="border:none">({attendees[0].position})</span></td>
                        </tr>
            """
            for attendee in attendees[1:]:
                section += f"""
                        <tr style="border:none; padding:1rem;">
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

        # Fetch partners based on groups separately
        board_members = self.env['res.partner'].search([
            ('user_ids.groups_id', 'in', board_member_group.id)
        ])
        board_secretaries = self.env['res.partner'].search([
            ('user_ids.groups_id', 'in', board_secretary_group.id)
        ])

        if is_confidential:
            # For confidential files, add both board members and board secretaries.
            partners_to_add = (board_members | board_secretaries).ids
        else:
            # For non-confidential files, remove board members from invitees,
            # but always include board secretaries.
            non_board_invitees = invitees - board_members
            partners_to_add = (non_board_invitees | board_secretaries).ids

        _logger.info("Adding partners for %s file. Partner IDs: %s",
                     "confidential" if is_confidential else "non-confidential", partners_to_add)

        # Search for existing attachments for this event with the same filename
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

        # Create or update the corresponding `product.document`
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
        Merge the cover file (from disk) with provided attachments, converting non-PDF files to PDF.
        Returns a tuple: (merged_stream, failed_attachments)
        """
        from PyPDF2 import PdfWriter, PdfReader
        from io import BytesIO
        import base64
        import logging

        _logger = logging.getLogger(__name__)
        self.ensure_one()
        merged_stream = BytesIO()
        pdf_writer = PdfWriter()
        pdf_writer.compress_content = False

        # Add cover file
        try:
            cover_reader = PdfReader(cover_file_path)
            for page in cover_reader.pages:
                pdf_writer.add_page(page)
        except Exception as e:
            _logger.error(f"Error reading cover file: {e}")
            raise UserError(_("Failed to read the cover file: %s") % cover_file_path)

        failed_attachments = []  # Collect errors here

        # Process attachments
        for attachment in attachments:
            try:
                attachment_data = base64.b64decode(attachment.datas)
                mime_type = attachment.mimetype
                file_name = (attachment.name or '').lower()

                # Check if conversion is needed
                if mime_type == 'application/pdf':
                    pdf_data = attachment_data
                else:
                    pdf_data = self._convert_to_pdf(attachment_data, mime_type, file_name)

                # Add pages from PDF data
                reader = PdfReader(BytesIO(pdf_data))
                for page in reader.pages:
                    pdf_writer.add_page(page)
            except Exception as e:
                _logger.error(f"Error processing attachment {attachment.name}: {e}")
                # Instead of raising an error, collect the error details:
                ext = attachment.name.split('.')[-1] if '.' in attachment.name else 'unknown'
                failed_attachments.append({
                    'name': attachment.name,
                    'extension': ext,
                    'error_message': str(e),
                })
                # Continue processing the remaining attachments
                continue

        pdf_writer.write(merged_stream)
        merged_stream.seek(0)
        return merged_stream, failed_attachments

    def _convert_to_pdf(self, data, mime_type, file_name):
        """Convert non-PDF data to PDF based on MIME type or file extension."""
        conversion_map = {
            'image/png': self._convert_image_to_pdf,
            'image/jpeg': self._convert_image_to_pdf,
            'image/gif': self._convert_image_to_pdf,
            'image/bmp': self._convert_image_to_pdf,
            'text/csv': self._convert_csv_to_pdf,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': self._convert_xlsx_to_pdf,
            'application/vnd.ms-excel': self._convert_xls_to_pdf,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._convert_docx_to_pdf,
        }

        # Determine converter
        if mime_type in conversion_map:
            return conversion_map[mime_type](data)
        elif file_name.endswith('.csv'):
            return self._convert_csv_to_pdf(data)
        elif file_name.endswith('.xlsx'):
            return self._convert_xlsx_to_pdf(data)
        elif file_name.endswith('.xls'):
            return self._convert_xls_to_pdf(data)
        elif file_name.endswith('.docx'):
            return self._convert_docx_to_pdf(data)
        elif file_name.endswith('.pptx'):
            return self._convert_pptx_to_pdf(data)
        elif any(file_name.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            return self._convert_image_to_pdf(data)
        else:
            raise UserError(_("Unsupported file type: %s") % file_name)

    def _convert_image_to_pdf(self, image_data):
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(image_data))
        pdf_buffer = BytesIO()
        img.save(pdf_buffer, format='PDF')
        return pdf_buffer.getvalue()

    def _convert_csv_to_pdf(self, csv_data):
        import csv
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        from io import StringIO

        csv_content = csv_data.decode('utf-8')  # Decode bytes to string
        reader = csv.reader(StringIO(csv_content))
        data = list(reader)

        if not data:
            raise ValueError("CSV file is empty")

        num_columns = len(data[0])

        # Choose orientation: Landscape for many columns, otherwise Portrait
        page_size = landscape(letter) if num_columns > 6 else letter
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=page_size, leftMargin=20, rightMargin=20, topMargin=20,
                                bottomMargin=20)

        # Calculate max column widths (based on longest content in each column)
        max_col_widths = [max(len(str(row[i])) for row in data) * 5 for i in range(num_columns)]

        # Limit column widths to fit the page
        max_page_width = doc.width  # Available width for content
        total_width = sum(max_col_widths)

        # Scale down column widths if they exceed page width
        if total_width > max_page_width:
            scale_factor = max_page_width / total_width
            col_widths = [w * scale_factor for w in max_col_widths]
            font_size = 6  # Reduce font size if scaling is needed
        else:
            col_widths = max_col_widths
            font_size = 8  # Default font size

        # Create table
        table = Table(data, colWidths=col_widths)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),  # Adjusted dynamically
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('WORDWRAP', (0, 0), (-1, -1)),  # Ensure text wraps inside columns
        ])
        table.setStyle(style)

        doc.build([table])
        return pdf_buffer.getvalue()

    def _convert_xlsx_to_pdf(self, xlsx_data):
        import pandas as pd
        from io import BytesIO
        # Read the Excel file into a DataFrame
        df = pd.read_excel(BytesIO(xlsx_data), engine='openpyxl')
        # Convert DataFrame to list-of-lists with header as first row
        data = [df.columns.tolist()] + df.values.tolist()
        return self._generate_pdf_from_table(data)

    def _generate_pdf_from_table(self, data):
        if not data:
            raise UserError(_("No data to generate PDF."))

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO

        num_columns = len(data[0])
        # Use landscape orientation if there are more than 6 columns
        page_size = landscape(letter) if num_columns > 6 else letter

        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer,
                                pagesize=page_size,
                                leftMargin=20,
                                rightMargin=20,
                                topMargin=20,
                                bottomMargin=20)
        available_width = doc.width  # Content width available after margins

        # Prepare raw text data (for width calculations)
        raw_data = [[str(cell) for cell in row] for row in data]

        # --- Determine Natural Column Widths & Font Size ---
        # We use a multiplier (points per character) to approximate width.
        # For a default font size of 10, try multiplier = 6.
        multiplier = 6
        natural_widths = [
            max(len(raw_data[row][col]) for row in range(len(raw_data))) * multiplier
            for col in range(num_columns)
        ]
        total_natural = sum(natural_widths)

        # If the total natural width exceeds the available width,
        # we reduce the font size (and multiplier) so more content fits.
        if total_natural > available_width:
            default_font_size = 6
            multiplier = 3.6  # Adjust multiplier for the smaller font
            natural_widths = [
                max(len(raw_data[row][col]) for row in range(len(raw_data))) * multiplier
                for col in range(num_columns)
            ]
            total_natural = sum(natural_widths)
        else:
            default_font_size = 10

        # Scale each column so that the table fills the available page width.
        scale_factor = available_width / total_natural if total_natural > 0 else 1
        col_widths = [w * scale_factor for w in natural_widths]

        # --- Convert cell content to Paragraphs for proper wrapping ---
        styles = getSampleStyleSheet()
        cell_style = styles["Normal"]
        cell_style.fontSize = default_font_size
        cell_style.leading = default_font_size * 1.2  # Slightly more than font size

        wrapped_data = []
        for row in data:
            wrapped_row = []
            for cell in row:
                # Each cell becomes a Paragraph so that long text wraps automatically.
                wrapped_row.append(Paragraph(str(cell), cell_style))
            wrapped_data.append(wrapped_row)

        # --- Create and Style the Table ---
        table = Table(wrapped_data, colWidths=col_widths)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ])
        table.setStyle(style)

        doc.build([table])
        return pdf_buffer.getvalue()

    def _convert_xls_to_pdf(self, xls_data):
        try:
            df = pd.read_excel(BytesIO(xls_data), engine='xlrd')  # Legacy Excel
            if df.empty:
                raise ValueError("XLS file is empty")

            data = [df.columns.values.tolist()] + df.values.tolist()

            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))

            # Auto-adjust column widths
            col_widths = [max(len(str(row[i])) for row in data) * 6 for i in range(len(data[0]))]
            col_widths = [min(w, 2 * inch) for w in col_widths]

            table = Table(data, colWidths=col_widths)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.lightgrey, colors.white])
            ])
            table.setStyle(style)

            doc.build([table])
            return pdf_buffer.getvalue()

        except Exception as e:
            raise ValueError(f"XLS conversion failed: {str(e)}")

    def _convert_docx_to_pdf(self, docx_data):
        # Create temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
            temp_docx.write(docx_data)
            temp_docx.flush()

            output_pdf = temp_docx.name.replace(".docx", ".pdf")

            # Convert DOCX to PDF using LibreOffice
            cmd = ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tempfile.gettempdir(), temp_docx.name]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            # Read the generated PDF
            with open(output_pdf, "rb") as pdf_file:
                pdf_data = pdf_file.read()

        return pdf_data

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

        # Generate the cover pages and get their file paths
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
        all_failed_errors = []

        # For Confidential: Merge cover page with all attachments
        if confidential_attachments or non_confidential_attachments or not (
                confidential_attachments and non_confidential_attachments):
            confidential_stream, confidential_errors = self._merge_attachments(
                confidential_cover_path, confidential_attachments + non_confidential_attachments
            )
            all_failed_errors += confidential_errors
            saved_documents["Confidential"] = self.save_merged_document(
                confidential_stream,
                filename_prefix=f"Boardpack_Confidential_{self.name}",
                description=f"Confidential document for event {self.name}"
            )

        # For Non-Confidential: Merge cover page with only non-confidential attachments
        if non_confidential_cover_path:
            if non_confidential_attachments:
                non_confidential_stream, non_confidential_errors = self._merge_attachments(
                    non_confidential_cover_path, non_confidential_attachments
                )
            else:
                non_confidential_stream = open(non_confidential_cover_path, 'rb')
                non_confidential_errors = []
            all_failed_errors += non_confidential_errors

            saved_documents["NonConfidential"] = self.save_merged_document(
                non_confidential_stream,
                filename_prefix=f"Boardpack_NonConfidential_{self.name}",
                description=f"Non-confidential document for event {self.name}"
            )

        _logger.info("Number of files saved: %d", len(saved_documents))
        for doc_type, attachment in saved_documents.items():
            if attachment:
                _logger.info("Saved document: %s (Type: %s)", attachment.name, doc_type)
            else:
                _logger.warning("No document saved for type: %s", doc_type)

        # If there were any errors, open a wizard to notify the user.
        if all_failed_errors:
            error_details = """
            <table style="width:100%; border: none;">
              <thead>
                <tr>
                  <th style="border:1px solid #ccc; padding:5px; text-align:left;">Attachment</th>
                </tr>
              </thead>
              <tbody>
            """
            for err in all_failed_errors:
                error_details += f"""
                <tr>
                  <td style="border:none; padding:5px;">{err['name']}</td>
                </tr>
                """
            error_details += """
              </tbody>
            </table>
            <p style="padding:1rem; border:1px solid black; margin-top:1rem; background-color:light-grey; color:crimson;">
                Please manually convert to PDF and re-upload the document(s).
            </p>
            """

            wizard = self.env['merge.error.wizard'].create({
                'error_message': error_details,
            })

            return {
                'name': _('The following files failed to convert to PDF and are not part of the Boardpack'),
                'view_mode': 'form',
                'view_id': self.env.ref('odoo_calendar_inheritence.merge_error_wizard_form_view').id,
                'res_model': 'merge.error.wizard',
                'res_id': wizard.id,
                'type': 'ir.actions.act_window',
                'target': 'new',
                # Pass the next action and also the original record’s ID and model name
                'context': {
                    'next_action': self.action_open_boardpack(),
                    'active_id': self.id,
                    'active_model': self._name,
                },
            }

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

    def action_publish_upload_minutes_documents(self):
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


class MergeErrorWizard(models.TransientModel):
    _name = 'merge.error.wizard'
    _description = 'Merge Error Notification'

    error_message = fields.Html(string="_", readonly=True)

    def action_continue(self):
        """Called when the user clicks the Continue button.
           This method updates the original record (setting is_board_park to True)
           and then proceeds with the next action.
        """
        # Retrieve the original record’s ID and model from the context
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if active_id and active_model:
            record = self.env[active_model].browse(active_id)
            record.write({'is_board_park': True})

        # Get the next action from the context and return it
        next_action = self.env.context.get('next_action')
        if next_action:
            return next_action
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Called when the user clicks the Cancel button.
           The boardpack saving process is aborted.
        """
        # You can add additional cleanup logic here if needed.
        return {'type': 'ir.actions.act_window_close'}