import requests
import csv
from bs4 import BeautifulSoup
import json


# 读取院系列表
def get_department_list(path):

    # 读取院系列表的csv文件
    with open(path, mode='r', encoding='utf-8') as f:
        departments = {}    # 以字典的形式保存院系信息（院系id: 院系名称）
        reader = csv.reader(f)
        for row in reader:
            departments[row[0]] = row[1]
    return departments


# 获取课程的名称
def analyze_course_title(tag):
    soup = BeautifulSoup(tag, 'html.parser')
    items = soup.select('td a')
    return items


# 获取课程的元数据
def analyze_course_metadata(tag):
    soup = BeautifulSoup(tag, 'html.parser')
    items = soup.select('td a td')
    return items


# 爬取课程数据
def crawl_html(header, url):

    html = requests.get(url, headers=header)
    html.encoding = 'gb2312'
    text = html.text
    soup = BeautifulSoup(text, 'html.parser')
    tags = soup.select('tr')

    id_courseTitle_list = []
    # 对于每个课程，进一步解析其标题和id，以及详细信息链接
    for tag in tags:
        # 获取课程的名称
        id_courseTitle = analyze_course_title(str(tag))
        if len(id_courseTitle) > 0:
            # print(id_courseTitle[0].attrs['href'])
            # 将课程详细信息链接、课程id、课程名称添加到列表id_courseTitle_list
            id_courseTitle_list.append(id_courseTitle[0].attrs['href']
                                       + ' ' + id_courseTitle[0].text
                                       + ' ' + id_courseTitle[1].text)
    # 对于每个课程，进一步解析其他元数据
    metadata_list = []
    for tag in tags:
        # 获取课程的其他元数据
        courseMetadata = analyze_course_metadata(str(tag))
        if len(courseMetadata) > 0:
            metadata_list.append(courseMetadata[0].text)

    # 返回课程的id与名称列表、其他元数据列表
    return id_courseTitle_list, metadata_list


# 获取课程详细信息
def get_course_detail_info(header, course_url):

    html = requests.get(course_url, headers=header)
    html.encoding = 'utf-8'
    temp = html.content
    # 对文本的编码进行处理（防止有一些内容解析不出来）
    text = str(temp)[2:-1].replace('\\n', '').replace('\\r', '').replace('\\t', '') \
        .encode('raw_unicode_escape').decode('unicode_escape') \
        .encode('raw_unicode_escape').decode('utf-8')
    soup = BeautifulSoup(text, 'html.parser')

    # 课程详细信息的HTML页面是表格形式的，tags1_text解析的是表格的表头，tags2_text解析的是表头对应的内容
    tags1 = soup.select('table tr th')
    tags2 = soup.select('table tr td span')

    tags1_text = [item.text for item in tags1 if item.text != '']
    tags2_text = [item.text for item in tags2]

    # 利用字典保存课程的详细信息
    course_detail_info = {}
    for i in range(len(tags2_text)):
        course_detail_info[tags1_text[i]] = tags2_text[i]

    return course_detail_info


if __name__ == '__main__':

    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36'
                            ' (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36'}

    # 获取院系列表
    departments = get_department_list('input/department_list.csv')

    # 爬取每个院系的课程信息
    for department in departments:

        result = []

        xs = department  # 院系编号
        xn = '20-21'    # 学年
        xq = '1'    # 学期，需要爬取两次，第一学期与第二学期
        nj = '%'    # 年级，%表示全部年级
        zy = '%'    # 专业，%表示全部专业

        # 构造院系课程信息url
        url = 'http://dean.pku.edu.cn/pkudean/course/kcbzy.php'\
              + '?xs=' + xs \
              + '&xn=' + xn \
              + '&xq=' + xq \
              + '&nj=' + nj \
              + '&zy=' + zy

        # 爬取当前院系的课程信息：
        # results_part1记录了课程的URL、id与名称；
        # results_part2中记录了课程的其他元数据（包括课程类型、任课教师、课程学分、课时长度等）
        results_part1, results_part2 = crawl_html(header, url)

        for i in range(len(results_part1)):
            course_url = results_part1[i].split()[0]
            course_id = results_part1[i].split()[1]
            course_name = results_part1[i].split()[2]
            course_type = results_part2[i].split()[1:4][0]
            course_length = results_part2[i].split()[1:4][2]

            # 由course_url访问课程详细信息页面，获取课程的详细信息
            course_info = get_course_detail_info(header, course_url)
            # 补充课程的基础信息
            course_info['课程名称'] = course_name
            course_info['课程类型'] = course_type
            course_info['课时'] = course_length
            course_info['开课院系'] = departments[department]

            if '课程号' in course_info.keys():
                print(course_info['开课院系'], course_info['课程号'], course_info['课程名称'])
                result.append(course_info)

        # 输出为json文件
        json_str = json.dumps(result, ensure_ascii=False, indent=4)
        with open('result/course_detail_info_' + xq + '_' + department + '.json', 'w', encoding='utf-8') as json_file:
            json_file.write(json_str)
