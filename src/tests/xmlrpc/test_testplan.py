# -*- coding: utf-8 -*-

import unittest

from six.moves.http_client import BAD_REQUEST
from six.moves.http_client import NOT_FOUND
from six.moves.http_client import INTERNAL_SERVER_ERROR

from django import test

from tcms.testcases.models import TestCase
from tcms.testcases.models import TestCasePlan
from tcms.testplans.models import TCMSEnvPlanMap
from tcms.testplans.models import TestPlan
from tcms.xmlrpc.api import testplan as XmlrpcTestPlan
from tcms.xmlrpc.api.testplan import import_case_via_XML
from tcms.xmlrpc.serializer import datetime_to_str
from tests.factories import ComponentFactory
from tests.factories import ProductFactory
from tests.factories import TCMSEnvGroupFactory
from tests.factories import TestCaseFactory
from tests.factories import TestPlanFactory
from tests.factories import TestPlanTypeFactory
from tests.factories import TestTagFactory
from tests.factories import UserFactory
from tests.factories import VersionFactory
from tests.testplans.test_importer import xml_file_without_error
from tests.xmlrpc.utils import make_http_request
from tests.xmlrpc.utils import XmlrpcAPIBaseTest

__all__ = (
    'TestAddComponent',
    'TestAddTag',
    'TestComponentMethods',
    'TestFilter',
    'TestGetAllCasesTags',
    'TestGetProduct',
    'TestGetTestCases',
    'TestGetTestRuns',
    'TestGetText',
    'TestImportCaseViaXML',
    'TestPlanTypeMethods',
    'TestRemoveTag',
    'TestUpdate',
)


class TestFilter(XmlrpcAPIBaseTest):

    @classmethod
    def setUpTestData(cls):
        cls.product = ProductFactory()
        cls.version = VersionFactory(product=cls.product)
        cls.tester = UserFactory()
        cls.plan_type = TestPlanTypeFactory(name='manual smoking')
        cls.plan_1 = TestPlanFactory(product_version=cls.version,
                                     product=cls.product,
                                     author=cls.tester,
                                     type=cls.plan_type)
        cls.plan_2 = TestPlanFactory(product_version=cls.version,
                                     product=cls.product,
                                     author=cls.tester,
                                     type=cls.plan_type)
        cls.case_1 = TestCaseFactory(author=cls.tester,
                                     default_tester=None,
                                     reviewer=cls.tester,
                                     plan=[cls.plan_1])
        cls.case_2 = TestCaseFactory(author=cls.tester,
                                     default_tester=None,
                                     reviewer=cls.tester,
                                     plan=[cls.plan_1])

    def test_filter_plans(self):
        plans = XmlrpcTestPlan.filter(None, {'pk__in': [self.plan_1.pk, self.plan_2.pk]})
        plan = plans[0]
        self.assertEqual(self.plan_1.name, plan['name'])
        self.assertEqual(self.plan_1.product_version.pk, plan['product_version_id'])
        self.assertEqual(self.plan_1.author.pk, plan['author_id'])

        self.assertEqual(2, len(plan['case']))
        self.assertEqual([self.case_1.pk, self.case_2.pk], plan['case'])
        self.assertEqual(0, len(plans[1]['case']))

    def test_filter_out_all_plans(self):
        plans_total = TestPlan.objects.all().count()
        self.assertEqual(plans_total, len(XmlrpcTestPlan.filter(None)))
        self.assertEqual(plans_total, len(XmlrpcTestPlan.filter(None, {})))


class TestAddTag(XmlrpcAPIBaseTest):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.http_req = make_http_request(user=cls.user,
                                         user_perm='testplans.add_testplantag')

        cls.product = ProductFactory()
        cls.plans = [
            TestPlanFactory(author=cls.user, owner=cls.user, product=cls.product),
            TestPlanFactory(author=cls.user, owner=cls.user, product=cls.product),
        ]

        cls.tag1 = TestTagFactory(name='xmlrpc_test_tag_1')
        cls.tag2 = TestTagFactory(name='xmlrpc_test_tag_2')
        cls.tag_name = 'xmlrpc_tag_name_1'

    def test_single_id(self):
        """Test with singal plan id and tag id"""
        self.assertRaisesXmlrpcFault(INTERNAL_SERVER_ERROR, XmlrpcTestPlan.add_tag,
                                     self.http_req, self.plans[0].pk, self.tag1.pk)

        XmlrpcTestPlan.add_tag(self.http_req, self.plans[0].pk, self.tag1.name)
        tag_exists = TestPlan.objects.filter(pk=self.plans[0].pk, tag__pk=self.tag1.pk).exists()
        self.assertTrue(tag_exists)

    def test_array_argument(self):
        XmlrpcTestPlan.add_tag(self.http_req, self.plans[0].pk, [self.tag2.name, self.tag_name])
        tag_exists = TestPlan.objects.filter(pk=self.plans[0].pk,
                                             tag__name__in=[self.tag2.name, self.tag_name])
        self.assertTrue(tag_exists.exists())

        plans_ids = [plan.pk for plan in self.plans]
        tags_names = [self.tag_name, 'xmlrpc_tag_name_2']
        XmlrpcTestPlan.add_tag(self.http_req, plans_ids, tags_names)
        for plan in self.plans:
            tag_exists = plan.tag.filter(name__in=tags_names).exists()
            self.assertTrue(tag_exists)


class TestAddComponent(XmlrpcAPIBaseTest):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.http_req = make_http_request(user=cls.user,
                                         user_perm='testplans.add_testplancomponent')

        cls.product = ProductFactory()
        cls.plans = [
            TestPlanFactory(author=cls.user, owner=cls.user, product=cls.product),
            TestPlanFactory(author=cls.user, owner=cls.user, product=cls.product),
        ]
        cls.component1 = ComponentFactory(name='xmlrpc test component 1',
                                          description='xmlrpc test description',
                                          product=cls.product,
                                          initial_owner=None,
                                          initial_qa_contact=None)
        cls.component2 = ComponentFactory(name='xmlrpc test component 2',
                                          description='xmlrpc test description',
                                          product=cls.product,
                                          initial_owner=None,
                                          initial_qa_contact=None)

    def test_single_id(self):
        XmlrpcTestPlan.add_component(self.http_req, self.plans[0].pk, self.component1.pk)
        component_exists = TestPlan.objects.filter(
            pk=self.plans[0].pk, component__pk=self.component1.pk).exists()
        self.assertTrue(component_exists)

    def test_ids_in_array(self):
        self.assertRaisesXmlrpcFault(BAD_REQUEST, XmlrpcTestPlan.add_component,
                                     self.http_req, [1, 2])

        plans_ids = [plan.pk for plan in self.plans]
        components_ids = [self.component1.pk, self.component2.pk]
        XmlrpcTestPlan.add_component(self.http_req, plans_ids, components_ids)
        for plan in TestPlan.objects.filter(pk__in=plans_ids):
            components_ids = [item.pk for item in plan.component.iterator()]
            self.assertTrue(self.component1.pk in components_ids)
            self.assertTrue(self.component2.pk in components_ids)


class TestPlanTypeMethods(XmlrpcAPIBaseTest):

    @classmethod
    def setUpTestData(cls):
        cls.http_req = make_http_request()
        cls.plan_type = TestPlanTypeFactory(name='xmlrpc plan type', description='')

    def test_check_plan_type(self):
        self.assertRaisesXmlrpcFault(BAD_REQUEST, XmlrpcTestPlan.check_plan_type, self.http_req)

        result = XmlrpcTestPlan.check_plan_type(self.http_req, self.plan_type.name)
        self.assertEqual(self.plan_type.name, result['name'])
        self.assertEqual(self.plan_type.description, result['description'])
        self.assertEqual(self.plan_type.pk, result['id'])

    def test_get_plan_type(self):
        result = XmlrpcTestPlan.get_plan_type(self.http_req, self.plan_type.pk)
        self.assertEqual(self.plan_type.name, result['name'])
        self.assertEqual(self.plan_type.description, result['description'])
        self.assertEqual(self.plan_type.pk, result['id'])

        self.assertRaisesXmlrpcFault(NOT_FOUND, XmlrpcTestPlan.get_plan_type, self.http_req, 0)
        self.assertRaisesXmlrpcFault(NOT_FOUND, XmlrpcTestPlan.get_plan_type, self.http_req, -2)


class TestGetProduct(XmlrpcAPIBaseTest):

    @classmethod
    def setUpTestData(cls):
        cls.http_req = make_http_request()
        cls.user = UserFactory()
        cls.product = ProductFactory()
        cls.plan = TestPlanFactory(author=cls.user, owner=cls.user, product=cls.product)

    def _verify_serialize_result(self, result):
        self.assertEqual(self.plan.product.name, result['name'])
        self.assertEqual(self.plan.product.description, result['description'])
        self.assertEqual(self.plan.product.disallow_new, result['disallow_new'])
        self.assertEqual(self.plan.product.vote_super_user, result['vote_super_user'])
        self.assertEqual(self.plan.product.max_vote_super_bug, result['max_vote_super_bug'])
        self.assertEqual(self.plan.product.votes_to_confirm, result['votes_to_confirm'])
        self.assertEqual(self.plan.product.default_milestone, result['default_milestone'])
        self.assertEqual(self.plan.product.classification.pk, result['classification_id'])
        self.assertEqual(self.plan.product.classification.name, result['classification'])

    def test_get_product(self):
        # self.assertRaisesXmlrpcFault(NOT_FOUND, XmlrpcTestPlan.get_product, self.http_req, 0)

        result = XmlrpcTestPlan.get_product(self.http_req, str(self.plan.pk))
        self._verify_serialize_result(result)

        result = XmlrpcTestPlan.get_product(self.http_req, self.plan.pk)
        self._verify_serialize_result(result)

        self.assertRaisesXmlrpcFault(BAD_REQUEST, XmlrpcTestPlan.get_product,
                                     self.http_req, 'plan_id')


@unittest.skip('TODO: test case is not implemented yet.')
class TestComponentMethods(test.TestCase):
    """TODO: """


@unittest.skip('TODO: test case is not implemented yet.')
class TestGetAllCasesTags(test.TestCase):
    """TODO: """


class TestGetTestCases(XmlrpcAPIBaseTest):
    """Test testplan.get_test_cases method"""

    @classmethod
    def setUpTestData(cls):
        cls.http_req = make_http_request()

        cls.tester = UserFactory(username='tester')
        cls.reviewer = UserFactory(username='reviewer')
        cls.product = ProductFactory()
        cls.plan = TestPlanFactory(author=cls.tester, owner=cls.tester, product=cls.product)
        cls.cases = [
            TestCaseFactory(author=cls.tester, default_tester=None, reviewer=cls.reviewer,
                            plan=[cls.plan]),
            TestCaseFactory(author=cls.tester, default_tester=None, reviewer=cls.reviewer,
                            plan=[cls.plan]),
            TestCaseFactory(author=cls.tester, default_tester=None, reviewer=cls.reviewer,
                            plan=[cls.plan]),
        ]
        cls.another_plan = TestPlanFactory(author=cls.tester, owner=cls.tester, product=cls.product)

    def test_get_test_cases(self):
        serialized_cases = XmlrpcTestPlan.get_test_cases(self.http_req, self.plan.pk)
        for case in serialized_cases:
            expected_case = TestCase.objects.filter(plan=self.plan.pk).get(pk=case['case_id'])

            self.assertEqual(expected_case.summary, case['summary'])
            self.assertEqual(expected_case.priority_id, case['priority_id'])
            self.assertEqual(expected_case.author_id, case['author_id'])

            plan_case_rel = TestCasePlan.objects.get(plan=self.plan, case=case['case_id'])
            self.assertEqual(plan_case_rel.sortkey, case['sortkey'])

    @unittest.skip('TODO: fix get_test_cases to make this test pass.')
    def test_different_argument_type(self):
        self.assertRaisesXmlrpcFault(BAD_REQUEST, XmlrpcTestPlan.get_test_cases,
                                     self.http_req, str(self.plan.pk))

    def test_404_when_plan_nonexistent(self):
        self.assertRaisesXmlrpcFault(NOT_FOUND, XmlrpcTestPlan.get_test_cases, self.http_req, 0)

        plan_id = TestPlan.objects.order_by('-pk')[:1][0].pk + 1
        self.assertRaisesXmlrpcFault(NOT_FOUND, XmlrpcTestPlan.get_test_cases,
                                     self.http_req, plan_id)

    def test_plan_has_no_cases(self):
        result = XmlrpcTestPlan.get_test_cases(self.http_req, self.another_plan.pk)
        self.assertEqual([], result)


@unittest.skip('TODO: test case is not implemented yet.')
class TestGetTestRuns(test.TestCase):
    """TODO: """


@unittest.skip('TODO: test case is not implemented yet.')
class TestGetText(test.TestCase):
    """TODO: """


@unittest.skip('TODO: test case is not implemented yet.')
class TestRemoveTag(test.TestCase):
    """TODO: """


class TestUpdate(test.TestCase):
    """ Tests the XMLRPM testplan.update method """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.http_req = make_http_request(user=cls.user,
                                         user_perm='testplans.change_testplan')

        cls.env_group_1 = TCMSEnvGroupFactory()
        cls.env_group_2 = TCMSEnvGroupFactory()
        cls.product = ProductFactory()
        cls.version = VersionFactory(product=cls.product)
        cls.tester = UserFactory()
        cls.plan_type = TestPlanTypeFactory(name='manual smoking')
        cls.plan_1 = TestPlanFactory(product_version=cls.version,
                                     product=cls.product,
                                     author=cls.tester,
                                     type=cls.plan_type,
                                     env_group=(cls.env_group_1,))
        cls.plan_2 = TestPlanFactory(product_version=cls.version,
                                     product=cls.product,
                                     author=cls.tester,
                                     type=cls.plan_type,
                                     env_group=(cls.env_group_1,))

    def test_update_env_group(self):
        # plan_1 and plan_2 point to self.env_group_1
        # and there are only 2 objects in the many-to-many table
        # so we issue XMLRPC request to modify the env_group of self.plan_2
        plans = XmlrpcTestPlan.update(self.http_req, self.plan_2.pk, {'env_group': self.env_group_2.pk})
        plan = plans[0]

        # now verify that the returned TP (plan_2) has been updated to env_group_2
        self.assertEqual(self.plan_2.pk, plan['plan_id'])
        self.assertEqual(1, len(plan['env_group']))
        self.assertEqual(self.env_group_2.pk, plan['env_group'][0])

        # and that plan_1 has not changed at all
        self.assertEqual(1, self.plan_1.env_group.count())
        self.assertEqual(self.env_group_1.pk, self.plan_1.env_group.all()[0].pk)

        # and there are still only 2 objects in the many-to-many table
        # iow no dangling objects left
        self.assertEqual(2, TCMSEnvPlanMap.objects.filter(plan__in=[self.plan_1, self.plan_2]).count())


class TestImportCaseViaXML(XmlrpcAPIBaseTest):
    """Test import_case_via_XML"""

    @classmethod
    def setUpTestData(cls):
        cls.author = UserFactory(username='user', email='user@example.com')
        cls.plan = TestPlanFactory(author=cls.author, owner=cls.author)
        cls.http_req = make_http_request(user=cls.author)

    def test_succeed_to_import_cases(self):
        result = import_case_via_XML(self.http_req,
                                     self.plan.pk,
                                     xml_file_without_error)

        self.assertEqual(2, TestCase.objects.count())
        self.assertTrue(TestCase.objects.filter(summary='case 2').exists())
        self.assertEqual('Success update 2 cases', result)


class TestGet(test.TestCase):
    """Test TestPlan.get"""

    @classmethod
    def setUpTestData(cls):
        cls.author = UserFactory(username='user', email='user@example.com')
        cls.http_req = make_http_request(user=cls.author)

        cls.product = ProductFactory()
        cls.version = VersionFactory(product=cls.product)
        cls.type = TestPlanTypeFactory(name='temp')
        cls.tag_fedora = TestTagFactory(name='fedora')
        cls.tag_centos = TestTagFactory(name='centos')

        cls.plan = TestPlanFactory(
            is_active=True,
            extra_link=None,
            product=cls.product,
            product_version=cls.version,
            owner=cls.author,
            author=cls.author,
            parent=None,
            type=cls.type,
            tag=[cls.tag_fedora, cls.tag_centos]
        )

    def test_get(self):
        self.maxDiff = None
        expected_plan = {
            'plan_id': self.plan.pk,
            'name': self.plan.name,
            'create_date': datetime_to_str(self.plan.create_date),
            'is_active': True,
            'extra_link': None,
            'product_version_id': self.version.pk,
            'product_version': self.version.value,
            'default_product_version': self.version.value,
            'owner_id': self.author.pk,
            'owner': self.author.username,
            'author_id': self.author.pk,
            'author': self.author.username,
            'product_id': self.product.pk,
            'product': self.product.name,
            'type_id': self.type.pk,
            'type': self.type.name,
            'parent_id': None,
            'parent': None,
            'attachment': [],
            'component': [],
            'env_group': [],
            'tag': ['centos', 'fedora']
        }

        plan = XmlrpcTestPlan.get(self.http_req, self.plan.pk)
        plan['tag'].sort()
        self.assertEqual(expected_plan, plan)