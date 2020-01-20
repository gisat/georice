import pandas, requests, numpy, datetime
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
import matplotlib.pyplot as plt
from requests.auth import HTTPBasicAuth


class TWProjects:
    HOLIDAYS = ['20200101', '20200410', '20200413', '20200501', '20200508', '20200705', '20200706', '20200928',
                '20201028', '20201117', '20201224', '20201225', '20201226', '20201230', '20201231']
    API_KEY = 'twp_5DRE9cHvMoEGKPyxi8rsLrNa88b8'
    ENDPOINT = 'gisat.teamwork.com'

    def __init__(self, tag, start, end, mans):
        self.plan = TWProjects.resources(start, end, mans)
        projects = TWProjects.get_projects_with_tag(tag)
        for project in projects:
            project_name = project['name'].replace(' ', '_')
            pt = TWProjects.get_project_timeline(project['project_id'], project_name, tag)
            self.plan = pandas.merge(self.plan, pt, left_index=True, right_index=True, how='outer')

    def plot(self):
        # base racecourses map
        labels = [l for l in self.plan.columns.values.__iter__()]
        res = self.plan.iloc[:, 0:3].cumsum(axis=1)
        cal = self.plan.iloc[:, 3:].cumsum(axis=1)
        for i in range(3):
            plt.plot_date(self.plan.index, res.iloc[:, i], linestyle='--', label=labels[i])
        for i in range(len(cal.columns)):
            plt.plot_date(self.plan.index, cal.iloc[:, i], linestyle='-', label=labels[i+3])

        plt.ylim(ymin=0)
        plt.gcf().autofmt_xdate()
        plt.xlabel('Date')
        plt.ylabel('Resources [h]')
        plt.grid()
        plt.legend()
        plt.show()
        plt.close()


    @staticmethod
    def resources(start, end, mp):
        """Return base pandas dataframe. Index is calnedar days between the start and end period. Working days have a
        calculated avalible man hours according to set manpower and working schema [0.6, 0.2, 0.2]"""
        cd = pandas.Series(0, index=pandas.date_range(start, end), name='cal')
        wd = TWProjects.working_days(start, end)
        array = numpy.full((len(wd), 3), 8*mp)*[0.6, 0.2, 0.2]
        w = pandas.DataFrame(data=array, index=wd, columns=['project', 'long', 'learn'])
        return pandas.merge(cd, w, left_index=True, right_index=True, how='outer').drop(columns='cal')

    @staticmethod
    def working_days(start, end):
        holidays = [pandas.to_datetime(d) for d in TWProjects.HOLIDAYS]
        return pandas.bdate_range(start, end, freq='C', weekmask='Mon Tue Wed Thu Fri', holidays=holidays)

    @staticmethod
    def get_project_timeline(project_id, name, tag):
        task_list = TWProjects._get_pandas_task_list(project_id, tag)
        return TWProjects.get_tasks_timeline(task_list, name)

    @staticmethod
    def get_tasks_timeline(task_list, name):
        tasks_timeline = pandas.DataFrame()
        for i in range(len(task_list)):
            task_time_range = TWProjects.working_days(task_list.loc[i, ['start-date']].values.item(),
                                                      task_list.loc[i, ['due-date']].values.item())
            if len(task_time_range) == 0:
                print(f'Wrong periond of the task https://gisat.teamwork.com/#/tasks/{task_list.loc[i,"id"]}')

            avg_est_hours = task_list.loc[i, ['estimated-minutes']]/60/len(task_time_range)
            task_timeline = pandas.DataFrame(data={name: avg_est_hours.values.item()}, index=task_time_range)
            tasks_timeline = tasks_timeline.add(task_timeline, fill_value=0)
        return tasks_timeline

    @staticmethod
    def has_tag(element, tag):
        try:
            if element['tags'][0]['name'] == tag:
                return True
        except IndexError:
            return False
        except KeyError:
            return False

    @staticmethod
    def get_projects_with_tag(tag):
        TWprojects = TWProjects.getfromTW('projects.json')
        projects = []
        for project in TWprojects['projects']:
            if TWProjects.has_tag(project, tag):
                    attr = {'name': 'name', 'project_id': 'id', }
                    projects.append(dict((k, project[v]) for k, v in attr.items()))
        return projects

    @staticmethod
    def _get_pandas_task_list(project_id, tag):
        attr = ['id', 'content', 'start-date', 'due-date', 'estimated-minutes', 'completed']
        tw_tasks = TWProjects.getfromTW(f'projects/{project_id}/tasks.json')
        t_list = pandas.DataFrame(columns=attr)
        for task in tw_tasks['todo-items']:
            if TWProjects.has_tag(task, tag):
                t_list = t_list.append(pandas.DataFrame(dict((a, task[a]) for a in attr), index=[0]), ignore_index=True)
        return t_list

    @staticmethod
    def getfromTW(trg):
        """Request get method for TW. Input trg: target to call"""
        url = f'https://{TWProjects.ENDPOINT}/{trg}'
        response = requests.get(url, auth=HTTPBasicAuth(TWProjects.API_KEY, 'xxx'))
        if response.status_code == 200:
            return response.json()
        else:
            print("Connection failed")
            quit()


if __name__ == "__main__":
    start='20200201'
    end='20200430'
    TWProjects('DEV', datetime.datetime.strptime(start, "%Y%m%d"), datetime.datetime.strptime(end, "%Y%m%d"), 3.5).plot()

print('')

