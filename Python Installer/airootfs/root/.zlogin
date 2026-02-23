# fix for screen readers
if grep -Fqa 'accessibility=' /proc/cmdline &> /dev/null; then
    setopt SINGLE_LINE_ZLE
fi

~/.automated_script.sh
xinit /bin/sh -c "python3 /usr/local/bin/installer.py" -- :0 vt1
