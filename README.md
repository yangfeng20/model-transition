# Model-Transition
## 模型转换
1. 入参模型转换出参模型
2. 模型字段关系映射
3. list映射list
4. list聚合对象
5. 对象映射对象
6. 对象拆分list
7. 规则配置简单


Model-Transition是一个将`来源数据模型`，通过指定的`映射规则`，生成/转换为`出参模型`。
同时支持自定义转换逻辑，动态导包，python代码动态执行。
<br>
<br>

使用场景一般为接口参数适配，接口代理转发，对象类型转换，模型转换。

<br>
<hr>
<br>

### 简单示例

```python
from core import ParameterMapper

# 输入模型数据
input_params_model = {
        "key": "model:1",
        "tags": ["用户", "公司"]
    }

rules = [
    # 注册根节点类型【第一条必须是定义根节点类型【 {} or [] 】】
    ("", "", "{}"),
    # 输入模型的key映射到输出模型的model.id，并添加自定义逻辑
    ("$.key", "$.model.id", "_cur + '-自定义处理' "),
    # list映射，并通过自定义函数处理
    ("$.tags", "$.model.tagList", "handler(_cur)"),

]

func_def = """
def handler(p):
    return str(p) + str(my_time.time())
"""
modules = ["time as my_time"]

mapper = ParameterMapper(rules, modules, func_def)
output_result = mapper.map_parameters(input_params_model)
print(output_result)
```

输出结果：
```json
{
  "model": {
    "id": "model:1-自定义处理",
    "tagList": [
      "用户1702610747.1056898",
      "公司1702610747.1056898"
    ]
  }
}
```
<br>
<hr>
<br>

### 规则配置说明
1. 规则配置是一个list，其中每一项是一个元组，表示字段映射关系。
2. 规则第一条必须是指定出参模型的根节点类型。[] or {}
    - `rules = [("", "", "{}"),...]`
3. 元组中有且仅有三个元素，分别代表不同的含义。
   - 第一个节点代表入参模型取值表达式
   - 第二个节点代表出参模型定义表达式
   - 第三个节点代表自定义取值逻辑表达式
4. 三个节点的关系是：首先获取入参模型表达式的值，然后通过自定义取值逻辑处理，最后赋值到出参模型定义表达式。
5. 在`入参模型取值表达式`中`$`表示根节点。`[`代表列表聚合。如果当前节点是list，并且没有`[`符合，表示列表映射。获取到的值是列表中的每个元素。
6. 在`自定义取值逻辑表达式`中，`_cur`代表前面`入参模型表达式`中获取到的值。`_i`表示输入对象。`_o`表示输出对象。
7. 在`出参模型定义表达式`中，list类型节点必须先注册，除非当前list节点后续不再有节点。
   - `("$.users", "$.userInfos", "[]")` 如果userInfos节点是list，那么就需要先注册,后续才能使用
    - `("$.users", "$.userInfos.tags")`
   - 如果`tags`节点也是list，但是tags后面没有其他节点，就可以直接使用tags节点，而不需要注册。
8. `list映射` 入参模型当前节点是list，映射到出参模型也是list。在`自定义转换表达式`中`_cur` 代表每个元素。会对list中的每一个元素调用当前表达式。
   - `("$.users.tags", "$.userInfos.tags","")`
   - `("$.users.tags[", "$.userInfos.tags","[i for i in _cur]")`
9. `list聚合` 入参模型当前节点是list，并且最后一个节点有`[`符合。表示聚合当前list。`_cur`代表整个list。
   - `("$.users.tags[", "$.userInfos.tags","")`
10. 非最后一个节点是list，自动取list中的每一项。
    - `("$.users.id", "$.userInfos.key","")` 自动取每一个user.id
    
<br>
<hr>
<br>

#### 配置示例
1. list输入映射对象输出
```python
input_params_model = [
    {
        "key": "model:1",
        "tags": ["用户", "公司"],
        "object": "abc",
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

# 输入list模型映射到出参对象类型
rules1 = [
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
```