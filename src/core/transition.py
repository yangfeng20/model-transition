class ParameterMapper:
    def __init__(self, mapping_rules, required_modules=None, *funcs):
        self.globals_context = {}
        self.local_context = {}

        self.mapping_rules = mapping_rules
        self.required_modules = required_modules or []
        self.required_func = funcs or []

        # 输入模型
        self.input_model = {}
        # 输出模型【往这个里面赋值】
        self.output_model_result = []

        """
        这两个用来确定list类型的输出对象的索引
        out_key ---> input_key ---> index
        """
        # 输出key和输入key关联关系
        self.output_input_link = {}
        # 输入key和索引关联关系
        self.input_index = {}

        # 导入全局模块和函数
        self.__import_module(self.required_modules, self.globals_context)

        # 导入全局函数
        for func in self.required_func:
            exec(func, self.globals_context, self.local_context)
            # self.globals_context[func.__name__] = func

        # 建立input output映射关系【list对象需要】
        for rule in self.mapping_rules[1:]:
            input_key, output_key_def = rule[:2]
            self.output_input_link[output_key_def] = input_key

    def evaluate_expression(self, expression, input_params, output_params, local_context):
        try:
            self.local_context['_i'] = input_params
            self.local_context['_o'] = output_params
            self.local_context['_cur'] = local_context

            # 如果global中和local中有相同函数，优先使用local的
            result = eval(expression, self.globals_context, self.local_context)
            return result
        except Exception as e:
            print(f"执行表达式 '{expression}' 时出错: {e}")
            return None

    @staticmethod
    def dict_get_key_val(dict_data, key):
        if key not in dict_data:
            # raise Exception(key + " key未在模型中: " + dict_data.__str__())
            return None
        return dict_data[key]

    def read_input_value(self, input_e, input_model):
        result = input_model
        e_node_list = input_e.split('.')
        e_node = e_node_list[0]
        # 根节点dict处理
        is_last_node = len(e_node_list) == 1
        if isinstance(input_model, dict) and input_e.find("$") != -1:
            e_node = e_node_list[1]
            is_last_node = len(e_node_list) == 2

        if e_node == "":
            raise Exception("input表达式不能为空")
        elif e_node.find("[") != -1:
            # 有list的取值表达式，必须是最后一个节点
            if not is_last_node:
                raise Exception(e_node + " list节点必须是最后一个节点")

            # 切除key的【[】标识；获取list数据
            result = self.dict_get_key_val(result, e_node[:-1])
            # 标注list取值，但是模型不是list
            if not isinstance(result, list) and result is not None:
                raise Exception(e_node + " 节点不是list")
            # 获取最后一个list，并且list取值，直接返回list
            yield result
            return
        # 没有list标注，同时也不是list
        elif not isinstance(result, list):
            if isinstance(result, dict):
                result = self.dict_get_key_val(result, e_node)
            # 如果是最后一层，并且是list，并且标注为获取list计算
            if is_last_node and e_node.find("[") != -1 and isinstance(result, list):
                yield result
                return
            elif not isinstance(result, list):
                yield result
                return
                # 没有list标注，但是当前数据是list，自动取每个元素
        for inner_index, auto_get_item in enumerate(result):
            # 列表对象取值，存储input_key与索引的映射关系
            self.input_index["$." + e_node if e_node.find("$") == -1 else e_node] = inner_index
            # 如果当前节点是最后一个节点，直接计算
            if is_last_node:
                yield auto_get_item
            else:
                root_key = ".".join(e_node_list[1:])
                # 根节点dict处理
                if isinstance(input_model, dict) and input_e.find("$") != -1:
                    root_key = ".".join(e_node_list[2:])
                result_gen = self.read_input_value(root_key, auto_get_item)
                for value in result_gen:
                    # 最后一个节点，是list，并且没有list聚合标识，那么就一个一个返回list中的数据
                    if root_key.find(".") == -1 and isinstance(value, list) and root_key.find("[") == -1:
                        for e_index, item in enumerate(value):
                            self.input_index[input_e] = e_index
                            yield item
                    else:
                        yield value

    def pre_handler(self):
        # 根节点为list时，映射入参和出参模型
        if isinstance(self.output_model_result, list):
            if not isinstance(self.input_model, list):
                raise Exception("输出模型根节点为list时，输入模型根节点也必须是list")
            self.output_input_link['$'] = '$'

    def map_parameters(self, input_model):
        # 从每条规则开始，每条规则对应多个value
        #         $.user.tags
        #         /     |    \
        #        [0]   [1]   [2]
        #      /        |       \
        #    user      user      user
        #  /  |  \    / |  \    /  |  \
        #  0  1   2  0  1   2   0  1   2
        # tags...
        # 每次先将一条规则的数据走到底

        # 初始化根对象数据类型
        self.output_model_result = eval(self.mapping_rules[0][2])
        self.input_model = input_model

        self.pre_handler()

        for rule in self.mapping_rules[1:]:
            input_key, output_key_def, expression = rule[:3]

            input_value_generator = self.read_input_value(input_key, input_model)
            for input_value in input_value_generator:
                # 存在自定义逻辑时执行自定义逻辑
                if expression:
                    # 使用自定义函数执行字符串形式的 Python 代码
                    output_value = self.evaluate_expression(expression, input_model, self.output_model_result,
                                                            input_value)
                else:
                    output_value = input_value

                # 输出模型无值，不进行赋值操作; 可能是入参模型就没有对应的字段;获取当前未聚合字段，但是list无值
                if output_value is None or (input_key.find("[") != -1 and not output_value):
                    continue
                # 将计算的值赋值到输出模型中
                self.set_val_to_model(input_key, output_key_def, output_value)

        return self.output_model_result

    def set_val_to_model(self, input_key, output_def, output_value):
        output_keys = output_def.split('.')
        current_output = self.output_model_result

        index_key = "$"
        for cur_out_key in output_keys[:-1]:
            # 输出根节点list处理
            if cur_out_key == "$" and isinstance(self.output_model_result, list):
                current_output = self.list_select_item(current_output, "$")
                continue
            if cur_out_key == "$":
                continue
            index_key += "." + cur_out_key
            if not isinstance(current_output, list):
                # 当前对象不是list，获取下级对象，没有就设置空的并获取
                current_output = current_output.setdefault(cur_out_key, {})
            if isinstance(current_output, list):
                current_output = self.list_select_item(current_output, index_key)

        # 是否将当前list映射到新的list
        if self.is_list_mapping(input_key) and not isinstance(output_value, list):
            # list第一次映射
            if output_keys[-1] not in current_output or len(current_output[output_keys[-1]]) < 1:
                # list映射时，当前list未在规则中单独注册list，自动填充空list
                if output_keys[-1] not in current_output:
                    current_output[output_keys[-1]] = []
            # 后续追加入list
            current_output[output_keys[-1]].append(output_value)
            return
        elif self.is_list_aggregation(input_key):
            pass

        # 更新current_output对象，直到前一个节点，然后复制
        current_output[output_keys[-1]] = output_value

    def is_list_aggregation(self, input_key):
        """
        list输入聚合，将输入模型为list的字段聚合为单值对象
        ("$.userList[", "$.userTotal", "handler(_cur)")
        此处的【_cur】是list对象
        """
        if not input_key.find("[") != -1:
            # 无聚合标识【[】
            return False
        # 有list聚合标识并且输入模型key路径是list
        return self.input_model_path_is_list(self.input_model, input_key[:-1])

    def is_list_mapping(self, input_key):
        """
        list输入映射，将输入模型为list的数据，其中的每个元素进行自定义处理，然后转换为新的list
        ("$.userList", "$.userDetail", "handler(_cur)")
        此处的【_cur】是list中的一个元素，会对list中的所有元素依次处理
        """
        # 列表默认是映射 一个list其中的每个元素通过一定的处理映射到另外一个list
        if input_key.find("[") != -1:
            # 无聚合标识【[】
            return False
        # 无list聚合标识并且输入模型key路径是list
        return self.input_model_path_is_list(self.input_model, input_key)

    def list_select_item(self, current_output, index_key):
        cur_out_link_input_key = self.output_input_link.get(index_key, None)
        if cur_out_link_input_key is None:
            raise Exception("当前输出模型索引：", index_key, "未映射输入模型索引")
        cur_list_index = self.input_index.get(cur_out_link_input_key, None)
        if cur_list_index is None:
            raise Exception("当前输出模型：", index_key, "映射到的输入模型: ", cur_out_link_input_key, "没有对应索引")
        if not self.index_exist(current_output, cur_list_index):
            current_output.append({})
        current_output = current_output[cur_list_index]
        return current_output

    @staticmethod
    def input_model_path_is_list(input_model, path):
        model = input_model
        for key in path.split(".")[1:]:
            if key.find("[") != -1:
                key = key[:-1]
            if isinstance(model, list):
                model = model[0]
            if key not in model:
                # return False
                raise Exception("路径错误")
            model = model[key]
        # 最后一层是否为list
        return isinstance(model, list)

    def add_func(self, func_str, *modules):
        self.__import_module(modules, self.local_context)
        exec(func_str, self.globals_context, self.local_context)

    @staticmethod
    def __import_module(module_list, context):
        for item in module_list:
            # 支持自定义模块别名
            splits = item.split("as")
            if len(splits) == 1:
                context[item] = __import__(item)
            elif len(splits) == 2:
                context[splits[1].strip()] = __import__(splits[0].strip())

    @staticmethod
    def index_exist(data_list, index):
        return len(data_list) >= index + 1

    @staticmethod
    def key_exist(data_dict, key):
        return key in data_dict
