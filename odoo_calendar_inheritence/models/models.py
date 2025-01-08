from PyPDF2 import PdfReader, PdfWriter
import re
from markupsafe import Markup
from bs4 import BeautifulSoup
import base64
import logging
import io
import re
from io import BytesIO
from markupsafe import Markup, escape
from PIL import Image, ImageFilter, ImageDraw, ImageFont
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
import pdfkit

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
    # bp_exists = fields.Boolean(compute='_compute_article_exists', store=False)
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

    employee_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_employee_partner_ids',
        store=False,
        string="Employee Partners"
    )

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

    def update_article_calendar(self):
        return ""

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

    def delete_article(self):
        """ Deletes the linked article if it exists. """
        if not self.article_id:
            raise ValidationError("No associated article found to delete!")

        # Log the article name for debugging
        _logger.info("Deleting Article: %s", self.article_id.name)

        try:
            # Unlink (delete) the article
            self.article_id.unlink()

            # Clear the reference on the agenda record
            self.article_id = False
            self.last_write_count = 0
            self.last_write_date = fields.Datetime.now()

            _logger.info("Article successfully deleted.")
        except Exception as e:
            _logger.error("Error deleting article: %s", str(e))
            raise ValidationError("An error occurred while deleting the article.")

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

        counter = 1
        company_id = self.env.company
        product_id = self.product_id.id
        logo = company_id.logo
        logo_html = (
            Markup('<img src="%s" class="bg-view" alt="Company Logo"/>') % self._get_src_data_b64(logo)
            if logo else ''
        )

        # Build agenda table
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
                    <td style="padding: 10px; border: 0px;">{description}</td>s
                    <td style="padding: 10px; border: 0px;">{presenters}</td>
                </tr>
            """).format(
                counter=counter,
                description=line.description or '',
                presenters=presenters or ''
            )
            counter += 1

        html_content += Markup("</tbody></table>")

        # Filter attendees by role
        board_attendees = []
        regular_attendees = []

        for attendee in self.attendees_lines_ids:  # Assuming self.attendees_ids has attendee lines
            if attendee.is_board_member or attendee.is_board_secretary:
                board_attendees.append(attendee)
            else:
                regular_attendees.append(attendee)

        # Generate Board Members Section
        board_attendees_content = Markup("")
        if board_attendees:
            board_attendees_content += Markup("<div><h3>Board Members</h3>")
            for attendee in board_attendees:
                position = f" ({attendee.position})" if attendee.position else ""
                board_attendees_content += Markup("<p>{attendee_name}   {position}</p>").format(
                    attendee_name=attendee.attendee_name, position=position
                )
            board_attendees_content += Markup("</div><hr/>")

        # Generate Regular Attendees Section
        regular_attendees_content = Markup("")
        if regular_attendees:
            regular_attendees_content += Markup("<div><h3>Other Attendees</h3>")
            for attendee in regular_attendees:
                position = f" ({attendee.position})" if attendee.position else ""
                regular_attendees_content += Markup("<p>{attendee_name}   {position}</p>").format(
                    attendee_name=attendee.attendee_name, position=position
                )
            regular_attendees_content += Markup("</div><hr/>")

        # Add description section
        description_content = Markup("")
        if self.description:
            description_content += Markup("""
                <div>
                    <h3>Description</h3>
                    <p>{description}</p>
                    <hr/>
                </div>
            """).format(description=self.description)

        # Build article body
        body_content = Markup("""
            <div>
                <header style="text-align: center;">
                    {logo_html}<br><br>
                    <h2><strong>{company_name}</strong></h2>
                </header>
                <div class="container">
                    <div class="card-body border-dark">
                        <div class="row no-gutters align-items-center">
                            <div class="col align-items-center">
                                <p class="mb-0"><span>{company_street}</span></p>
                                <p class="mb-0"><span>{company_city}</span></p>
                                <p class="m-0"><span>{company_country}</span></p>
                            </div>
                            <div class="col-auto">
                                <div class="float-right text-end">
                                    <p class="mb-0 float-right"><span>{company_phone}</span></p>
                                    <p class="mb-0 float-right"><span>{company_email}</span></p>
                                    <p class="mb-0 float-right"><span>{company_website}</span></p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div><br><hr>
                <div class="container">
                    <p><strong>Title: </strong> {event_name}</p>
                    <p><strong>Start Date:</strong> {start_date}</p>
                    <p><strong>Organizer:</strong> {organizer}</p>
                </div>
                <hr/>
                {description_content}
                <h3>Agenda</h3>
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
            description_content=description_content,
            board_attendees_content=board_attendees_content,
            regular_attendees_content=regular_attendees_content,
            html_content=html_content
        )

        # Create or update the article
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

            for attendee in self.attendees_lines_ids:
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
                    <thead>
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
                    <tr style="border: 0px;">
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
                    description=line.description or ''
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
            # Retrieve the related employee and position
            employee = self.env['hr.employee'].search([('work_email', '=', partner.email)], limit=1)
            position = employee.job_id.name if employee else 'Unknown Position'

            # Log the partner and their position
            _logger.info("Attendee: %s, Position: %s", partner.name, position)

            # Check if the partner is linked to a user
            user = self.env['res.users'].search([('partner_id', '=', partner.id)], limit=1)
            if user:
                # Check the user's group membership
                is_board_member = user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_member')
                is_board_secretary = user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_secretary')

                # Log group membership
                if is_board_member or is_board_secretary:
                    role = 'Board Member' if is_board_member else 'Board Secretary'
                    _logger.info("Attendee %s is a %s", partner.name, role)
                else:
                    _logger.info("Attendee %s does not belong to any board-related group", partner.name)

            # Add attendee details
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

    def action_open_boardpack(self):
        self.ensure_one()

        # Fetch Confidential and NonConfidential boardpacks
        confidential_attachment_id = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            ('name', 'ilike', f"{self.name}_Confidential.pdf")
        ], limit=1)

        non_confidential_attachment_id = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id),
            ('name', 'ilike', f"{self.name}_NonConfidential.pdf")
        ], limit=1)

        # Check if user is Board Member or Board Secretary
        is_board_member_or_secretary = self.env.user.has_group(
            'odoo_calendar_inheritence.group_agenda_meeting_board_member') or \
                                       self.env.user.has_group(
                                           'odoo_calendar_inheritence.group_agenda_meeting_board_secretary')

        # Determine accessible files
        accessible_attachment_ids = []
        if non_confidential_attachment_id:
            accessible_attachment_ids.append(non_confidential_attachment_id.id)
        if is_board_member_or_secretary and confidential_attachment_id:
            accessible_attachment_ids.append(confidential_attachment_id.id)

        # Log accessible attachments
        _logger.info("User %s is accessing the following attachments: %s",
                     self.env.user.name, accessible_attachment_ids)

        # Check if no files are accessible
        if not accessible_attachment_ids:
            _logger.info("No accessible attachments for user %s on event %s", self.env.user.name, self.name)
            return {'type': 'ir.actions.act_window_close'}

        # Fetch matching product documents
        matching_documents = self.env['product.document'].search(
            [('ir_attachment_id', 'in', accessible_attachment_ids)])
        _logger.info("Matching Product Document count for user %s: %d", self.env.user.name, len(matching_documents))

        # Log retrieved document names
        _logger.info("User %s retrieved the following documents: %s", self.env.user.name,
                     matching_documents.mapped('name'))

        # Return action to open documents
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'product.document',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', matching_documents.ids)],
            'context': {'default_res_model': 'calendar.event', 'default_res_id': self.id},
        }

    def action_open_documents(self):
        self.ensure_one()

        # Fetch Confidential and NonConfidential boardpacks
        confidential_attachment_ids = []
        non_confidential_attachment_ids = []
        for suffix in ["Confidential", "NonConfidential"]:
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'calendar.event'),
                ('res_id', '=', self.id),
                ('name', 'ilike', f"{self.name}_{suffix}.pdf")
            ], limit=1)
            if attachment:
                if "Confidential" in suffix:
                    confidential_attachment_ids.append(attachment.id)
                else:
                    non_confidential_attachment_ids.append(attachment.id)
            else:
                _logger.info(f"No attachment found for {suffix} file for event {self.name}")

        # Fetch unrestricted attachments
        unrestricted_attachment_ids = []
        for line in self.product_line_ids:
            if not line.is_user_restricted:
                unrestricted_attachment_ids.extend(line.pdf_attachment.ids)

        # Check if user is Board Member or Board Secretary
        is_board_member_or_secretary = self.env.user.has_group(
            'odoo_calendar_inheritence.group_agenda_meeting_board_member') or \
                                       self.env.user.has_group(
                                           'odoo_calendar_inheritence.group_agenda_meeting_board_secretary')

        # Combine all accessible files
        all_attachment_ids = unrestricted_attachment_ids + non_confidential_attachment_ids
        if is_board_member_or_secretary:
            all_attachment_ids += confidential_attachment_ids

        # Log the final list of accessible attachments
        _logger.info("User %s is accessing the following attachments: %s",
                     self.env.user.name, all_attachment_ids)

        # Check if no files are found
        if not all_attachment_ids:
            _logger.info("No accessible attachments for user %s on event %s", self.env.user.name, self.name)
            return {'type': 'ir.actions.act_window_close'}

        # Fetch matching product documents
        matching_documents = self.env['product.document'].search([('ir_attachment_id', 'in', all_attachment_ids)])
        _logger.info("Matching Product Document count for user %s: %d", self.env.user.name, len(matching_documents))

        # Log retrieved document names
        _logger.info("User %s retrieved the following documents: %s", self.env.user.name,
                     matching_documents.mapped('name'))

        # Return action to open documents
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'product.document',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', matching_documents.ids)],
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

    def add_media_placeholder(self, pdf_writer, media_files):
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

    def save_merged_document(self, pdf_stream, filename_suffix, description):
        """
        Save a single PDF document to `ir.attachment` and associate it with `product.document`.
        Add invitees from `calendar.event` and specific groups to `partner_ids`.
        """
        self.ensure_one()

        # Reset the stream pointer before reading
        if pdf_stream.seekable():
            pdf_stream.seek(0)

        filename = f"{self.name}{filename_suffix}"
        _logger.info("Processing file: %s (suffix: %s)", filename, filename_suffix)

        # Log all invitees for the calendar event
        invitees = self.partner_ids
        _logger.info("Invitees for calendar.event '%s': %s", self.name, [partner.name for partner in invitees])

        # Determine the confidentiality status
        is_confidential = "NonConfidential" in filename_suffix
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
        if is_confidential:
            partners_to_add =invitees.ids
            _logger.info("Adding board members and secretaries as partners for confidential file.")
        else:
            partners_to_add = board_partners.ids
            _logger.info("Adding invitees as partners for non-confidential file. Invitee IDs: %s", partners_to_add)

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

    def add_watermark_to_pdf(self, page):
        """
        Apply watermark to a PDF page unless the context specifies no restrictions.
        """
        # Check context or conditions to skip watermarking
        if self.env.context.get('skip_watermark', False):
            return page

        # Apply watermark as usual
        page_width = int(float(page.mediabox.width))
        page_height = int(float(page.mediabox.height))

        # Create a blank canvas for the page
        page_image = Image.new('RGB', (page_width, page_height), color=(255, 255, 255))  # White background
        blurred_image = page_image.filter(ImageFilter.GaussianBlur(radius=10))

        # Draw watermark text
        draw = ImageDraw.Draw(blurred_image)
        font = ImageFont.load_default()  # Load a default font
        watermark_text = "RESTRICTED"
        text_width, text_height = draw.textsize(watermark_text, font=font)
        text_position = ((page_width - text_width) // 2, (page_height - text_height) // 2)
        draw.text(text_position, watermark_text, fill=(255, 0, 0), font=font)

        # Convert to PDF page
        rgb_image = blurred_image.convert('RGB')
        image_pdf = io.BytesIO()
        rgb_image.save(image_pdf, format='PDF')
        image_pdf.seek(0)
        image_reader = PdfReader(image_pdf)

        # Merge watermark with original page
        page.merge_page(image_reader.pages[0])
        return page

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

    def _merge_attachments(self, cover_stream, attachments, restricted=True):
        """
        Merge cover stream with provided attachments.
        For restricted users, apply a watermark to all pages of the attachments.
        """
        self.ensure_one()
        merged_stream = io.BytesIO()
        pdf_writer = PdfWriter()

        # Add the cover page without watermark
        cover_reader = PdfReader(cover_stream)
        pdf_writer.add_page(cover_reader.pages[0])

        # Check if the user is restricted
        is_restricted_user = restricted and self.env.user.partner_id not in self.Restricted

        # Add attachments with or without watermark
        for attachment in attachments:
            attachment_reader = PdfReader(io.BytesIO(base64.b64decode(attachment.datas)))
            for page in attachment_reader.pages:
                if is_restricted_user:
                    # Apply watermark to the page for restricted users
                    page = self._add_watermark_to_page(page)
                pdf_writer.add_page(page)

        # Write the final merged PDF
        pdf_writer.write(merged_stream)
        merged_stream.seek(0)
        return merged_stream

    def _generate_cover_html(self, company_logo_base64):
        """
        Generate HTML content for the cover page, including the company logo.
        Add CSS for page breaks to ensure proper content flow in the PDF.
        """
        if not self.article_id or not self.article_id.body:
            raise UserError(_("No associated article found to generate the cover page."))

        html_content = self.article_id.body
        _logger.info("Original HTML Content: %s", html_content)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        html_content = html_content.replace('/web/image', f'{base_url}/web/image')

        _logger.info("Updated HTML Content with Base URL: %s", html_content)

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

        # Split content and add page breaks
        html_content_with_logo += f"""
        <div>
            <div class="content-section">
                {html_content}
            </div>
            <div class="page-break"></div>
            <div class="content-section">
                <h3>Additional Content</h3>
                <p>Include more details here.</p>
            </div>
        </div>
        </body>
        </html>
        """

        return html_content_with_logo

    def _generate_cover_pdf(self, html_content_with_logo):
        """
        Generate a PDF from the cover page HTML content using wkhtmltopdf.
        """
        _logger.info("HTML Content before PDF Conversion: %s", html_content_with_logo)

        pdf_cover_stream = io.BytesIO()
        try:
            # Create a temporary HTML file to pass to wkhtmltopdf
            with open('/tmp/temp_cover_page.html', 'w', encoding='utf-8') as f:
                f.write(html_content_with_logo)

            # Run wkhtmltopdf command to convert the HTML to PDF
            result = subprocess.run(
                ['wkhtmltopdf', '/tmp/temp_cover_page.html', '/tmp/temp_cover_page.pdf'],
                capture_output=True, text=True
            )

            # Check for errors in the wkhtmltopdf process
            if result.returncode != 0:
                _logger.error("wkhtmltopdf error: %s", result.stderr)
                raise UserError(_("Failed to generate cover PDF: %s") % result.stderr)

            # Read the generated PDF file into memory
            with open('/tmp/temp_cover_page.pdf', 'rb') as pdf_file:
                pdf_cover_stream.write(pdf_file.read())

            _logger.info("Cover page PDF generated successfully.")

        except Exception as e:
            _logger.error("Failed to generate cover PDF: %s", str(e))
            raise UserError(_("Failed to generate cover PDF: %s") % str(e))

        # Rewind the stream to the beginning
        pdf_cover_stream.seek(0)
        return pdf_cover_stream

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
        Stream the appropriate document based on user roles.
        """
        self.ensure_one()

        # Step 1: Fetch the company logo and generate cover page
        company_logo_base64 = self._get_company_logo_base64()
        html_content_with_logo = self._generate_cover_html(company_logo_base64)

        # Generate the cover page PDF
        pdf_cover_stream = self._generate_cover_pdf(html_content_with_logo)

        # Step 2: Classify attachments into confidential and non-confidential
        confidential_attachments, non_confidential_attachments = self._classify_attachments()

        _logger.info("Confidential Attachments: %d", len(confidential_attachments))
        _logger.info("Non-Confidential Attachments: %d", len(non_confidential_attachments))

        if not confidential_attachments and not non_confidential_attachments:
            _logger.warning("No attachments found to merge.")
            return {}

        # Step 3: Generate streams
        # For Confidential: Merge cover page with all attachments
        confidential_stream = self._merge_attachments(
            pdf_cover_stream, confidential_attachments + non_confidential_attachments, restricted=True
        )

        # For Non-Confidential: Merge cover page with only non-confidential attachments
        non_confidential_stream = self._merge_attachments(
            pdf_cover_stream, non_confidential_attachments, restricted=False
        )

        # Step 4: Save the documents
        saved_documents = {
            "Confidential": self.save_merged_document(
                confidential_stream,
                filename_suffix="_Confidential.pdf",
                description=f"Confidential document for event {self.name}"
            ),
            "NonConfidential": self.save_merged_document(
                non_confidential_stream,
                filename_suffix="_NonConfidential.pdf",
                description=f"Non-confidential document for event {self.name}"
            ),
        }

        # Log details of saved documents
        _logger.info("Number of files saved: %d", len(saved_documents))
        for doc_type, attachment in saved_documents.items():
            if attachment:
                _logger.info("Saved document: %s (Type: %s)", attachment.name, doc_type)
            else:
                _logger.warning("No document saved for type: %s", doc_type)

        # Step 5: Determine user access level
        user_has_access = self.env.user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_secretary') or \
                          self.env.user.has_group('odoo_calendar_inheritence.group_agenda_meeting_board_member')

        action = self.action_open_boardpack()

        # Explicitly return the action to propagate it
        return action


class AgendaLines(models.Model):
    _name = 'agenda.lines'
    _description = 'Agenda Lines'

    calendar_id = fields.Many2one('calendar.event', string="Calendar")
    description = fields.Html(related='calendar_id.agenda_description')
    partner_ids = fields.Many2many('res.partner', string='Attendees')
    duration = fields.Float(related="calendar_id.duration", string='Duration')
    agenda_attachment_ids = fields.Many2many(comodel_name='ir.attachment', string="Attachments")
