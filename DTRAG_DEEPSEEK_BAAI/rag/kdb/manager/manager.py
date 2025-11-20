from rag.kdb.db import db


class Manager:
    def auth_user(self, user, doc_group, allowed=True):
        """
        user：用户标识，如果是所有用户可以使用 "*"
        doc_group: 文档组，manager是基于文档组来控制访问权限
        allowed: 如果为True表示允许访问，如果为False表示禁止访问
        """

        user = str(user)
        allowed_users = []
        permission = db.instance.get_doc_group_permission(doc_group)
        if permission is not None and len(permission) > 0:
            allowed_users = permission[0]["allowed_users"].split(",")

        if allowed:
            if "*" in allowed_users:
                return
            if user not in allowed_users:
                allowed_users.append(user)

        else:
            if "*" in allowed_users:
                allowed_users.append("-" + user)
            elif user in allowed_users:
                allowed_users.remove(user)
            else:
                return

        db.instance.add_doc_group_permission(doc_group, allowed_users)

    # 发布指定文档版本
    def publish_doc_ver(self, doc_ver_id):
        db.instance.publish_doc_ver(doc_ver_id)

    # 发布最新文档版本
    def publish_lastest_doc_ver(self, doc_name):
        db.instance.publish_lastest_doc_ver(doc_name)

    # 获取用户可访问的文档版本
    def get_allowed_access_doc_ver_ids(self, user, doc_group):
        if not self._check_allowed_access(user, doc_group):
            return []

        return db.instance.get_lastest_doc_ver_ids(doc_group)

    # 检查权限
    def _check_allowed_access(self, user, doc_group=""):
        user = str(user)
        permission = db.instance.get_doc_group_permission(doc_group)
        if permission is not None and len(permission) > 0:
            allowed_users = permission[0]["allowed_users"].split(",")
            if "*" in allowed_users:
                if ("-" + user) not in allowed_users:
                    return True
                else:
                    return False
            elif user in allowed_users:
                return True
            elif user == "":
                return True
            else:
                return False
        else:
            return False


instance = Manager()
