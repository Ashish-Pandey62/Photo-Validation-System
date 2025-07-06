import tkinter
from tkinter.filedialog import askdirectory, askopenfilename
import os

def opendialogForDirectory(type):
    root = tkinter.Tk()
    currdir = os.getcwd()
    if type == 'folder':
        dirname = askdirectory(parent=root, initialdir=currdir, title='Please select a directory')

    else:
        dirname = askopenfilename(parent=root, initialdir=currdir, title="Select file",
                                                     filetypes=[('all files', '.*'),
                                                                ('image files', ('.png', '.jpg','.JPG','.JPEG','.PNG')),
                                                                ]
                                                     )
    root.withdraw()
    
    return dirname
