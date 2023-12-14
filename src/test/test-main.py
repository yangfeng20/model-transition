from core import ParameterMapper
input_params_model = [
    {
        "key": "model:1",
        "tags": ["用户", "公司"],
        "user": [
            {"key": "model:1:user:1",
             "tags": [1, 2, 3]
             },
            {"key": "model:1:user:2",
             "tags": [4, 5, 6]
             }
        ]
    },
    {
        "key": "model:2",
        "tags": ["客户"],
        "user": [
            {"key": "model:2:user:1",
             "tags": [7, 8, 9]
             },
            {"key": "model:1:user:2",
             "tags": [11, 22, 33]
             },
            {"key": "model:1:user:3",
             "tags": [100, 222, 355]
             }
        ]
    },
]

rules = [
    # 注册根节点类型【第一条必须是定义根节点类型【 {} or [] 】】
    ("", "", "{}"),
    # list节点必须注册【触发当前list节点后续不会在使用，也就是不会出现在出参模型中】
    ("$", "$.model", "[]"),
    # 注册list节点【标识：$.model.userInfo 是一个list，并映射到入参模型的$.user】
    ("$.user", "$.model.userInfo", "[]"),
    # 映射list。将入参模型list中的每一项做一定处理之后，生成新的出参模型list
    ("$.tags", "$.model.tag", 'handler(_cur)'),
    # 映射普通字段对应关系，并做对应处理
    ("$.user.key", "$.model.userInfo.id", "_cur"),
    # 【[】表示聚合list，将list作为一个整体来处理，但是这实际是一个映射，因为在转换逻辑中编写了列表推导式
    ("$.tags[", "$.model.tags", '[ str(i) +" - tags" for i in _cur or []]'),
    # 聚合列表，将tags列表聚合为了一个字符串【当前也是list节点，但是不用注册，因为tags没有后续节点】
    ("$.user.tags[", "$.model.userInfo.companyInfo.tags", "str(_cur) + ' - desc'"),
    ("$.user.company.name", "$.model.userInfo.companyInfo.name", ""),
    ("$.user.company.id", "$.model.userInfo.companyInfo.id", ""),

]


func_def = """

def handler(tags):
    result = ""
    for i in tags:
        result +=str(i) + " " + str(my_time.time()) + " "
    return result


"""

modules = ["time as my_time"]


mapper = ParameterMapper(rules, modules, func_def)
output_result = mapper.map_parameters(input_params_model)
print(output_result)
