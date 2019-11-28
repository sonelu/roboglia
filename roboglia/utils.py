

def readIniFile(filename):

    result = {}
    if filename == '':
        return result
        
    with open(filename, 'r') as f:

        current_section = None
        section_content = []
        content_size = 0
        for index, line in enumerate(f.readlines()):
            # Remove comments
            start = line.find('#')
            if start >= 0:
                line = line[0:start]
            # Check if a new section
            if line.find('[') >= 0:
                if current_section != None:
                    result[current_section] = section_content
                    current_section = None
                    section_content = []
                    content_size = 0
                line = line.strip()
                current_section = line[line.find('[')+1:line.find(']')]
            # Check content
            if line.find('|') >= 0:
                if current_section == None:
                    raise ValueError('Content of INI file without a prior section in line {}'.format(index+1))
                data = line.split('|')
                data = [item.strip() for item in data]
                if content_size == 0:
                    content_size = len(data)
                    fields = data
                else:
                    if len(data) != content_size:
                        raise ValueError('Data section with inconsistent number of fields: {}, expected {} at line {}'.format(len(data), content_size, index+1))
                    else:
                        section_content.append(dict(zip(fields, data)))
        # at the end add the lastsection
        if current_section != None:
            result[current_section] = section_content

        return result