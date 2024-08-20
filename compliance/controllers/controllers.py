# -*- coding: utf-8 -*-
# from odoo import http


# class Compliance(http.Controller):
#     @http.route('/compliance/compliance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/compliance/compliance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('compliance.listing', {
#             'root': '/compliance/compliance',
#             'objects': http.request.env['compliance.compliance'].search([]),
#         })

#     @http.route('/compliance/compliance/objects/<model("compliance.compliance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('compliance.object', {
#             'object': obj
#         })

