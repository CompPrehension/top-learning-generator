# html2img.py
# https://github.com/jarrekk/imgkit

# c:/D/Work/4labs/wkhtmltopdf/bin/wkhtmltoimage.exe


try:
    import imgkit  # pip install imgkit
except ModuleNotFoundError:
    print('import error: module `imgkit` is not installed. This will break calls to html2jpg(). Use: pip install imgkit')

from crop_png import crop_image


def config():
    return imgkit.config(
        wkhtmltoimage='c:/D/Work/4labs/wkhtmltopdf/bin/wkhtmltoimage.exe')  # to install: visit https://wkhtmltopdf.org/


def options():
    return {
        # 'format': 'png',  # file is 36 times larger than jpg
        # 'format': 'jpg',
        'encoding': "UTF-8",
        'log-level': "none",
    }


def change_ext(filepath, target_ext='.jpg'):
    return os.path.splitext(filepath)[0] + target_ext


def html2jpg(file_in='c:/D/Work/YDev/CompPr/c_owl/code_gen/test.html', file_out='out.jpg', crop=True):
    imgkit.from_file(file_in, file_out, options=options(), config=config())

    if crop:
        crop_image(file_out)


def html_string2jpg(string_in='<h1>Hello world...</h1>', file_out='out.jpg', crop=True):
    imgkit.from_string(string_in, file_out, options=options(), config=config())

    if crop:
        crop_image(file_out)


# imgkit.from_url('http://google.com', 'out.jpg')
# imgkit.from_string('Hello!', 'out.jpg')


def html_2_jpg_batch(dir_src=r'c:\Temp2\cntrflowoutput_v6_html', dest_dir=r'c:\Temp2\cntrflowoutput_v6_jpg',
                     ext_pattern='*.html', limit=0, crop=True):
    'convert all .html files in DIR_SRC to *.jpg into DEST_DIR'
    from glob import glob

    for i, fp in enumerate(glob(os.path.join(dir_src, ext_pattern))):
        if limit and i >= limit:
            print('stop on limit', limit)
            break

        print(f'[{i + 1}]\t', fp, end='\t')

        out = change_ext(
            os.path.join(
                dest_dir,
                os.path.split(fp)[1]),
            '.jpg')

        html2jpg(fp, out, crop=crop)
        print('OK')


if __name__ == '__main__':
    if 0:
        import os.path

        # html_2_jpg_batch(dir_src=r'c:\Temp2\cntrflowoutput_v6_fg_html',
        # 	dest_dir=r'c:\Temp2\cntrflowoutput_v6_fg_html',
        # 	limit=10, crop=bool(1))

        html_2_jpg_batch(dir_src=r'c:\Temp2\manual_html',
                         dest_dir=r'c:\Temp2\manual_jpg',
                         # limit=10,
                         crop=bool(1))

        exit(0)

    # in_path = r'c:\Temp2\cntrflowoutput_v6_html\ijkurlhook_seek__16942028069541267316__1643030096.html'
    in_path = r'c:\D\Work\YDev\CompPr\c_owl\code_gen\test.html'
    out_path = 'out.jpg'
    html2jpg(in_path, out_path)

    # crop_image(out_path)

    print('done.')
