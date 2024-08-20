# -*- coding: utf-8 -*-
from odoo import http


class OdooCalendarInheritence(http.Controller):
    @http.route('/odoo_calendar_inheritence/odoo_calendar_inheritence', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/odoo_calendar_inheritence/odoo_calendar_inheritence/objects', auth='public')
    def list(self, **kw):
        return http.request.render('odoo_calendar_inheritence.listing', {
            'root': '/odoo_calendar_inheritence/odoo_calendar_inheritence',
            'objects': http.request.env['odoo_calendar_inheritence.odoo_calendar_inheritence'].search([]),
        })

    @http.route('/odoo_calendar_inheritence/odoo_calendar_inheritence/objects/<model("odoo_calendar_inheritence.odoo_calendar_inheritence"):obj>', auth='public')
    def object(self, obj, **kw):
        return http.request.render('odoo_calendar_inheritence.object', {
            'object': obj
        })

