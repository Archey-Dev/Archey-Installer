#include <QApplication>
#include <QFont>
#include <QScreen>
#include "MainWindow.h"

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setApplicationName("Archey");
    app.setApplicationVersion("0.1.0");
    app.setFont(QFont("IBM Plex Mono", 13));

    MainWindow window;

    // Fullscreen, frameless — same as the Python version
    QScreen* screen = app.primaryScreen();
    window.setGeometry(screen->geometry());
    window.setWindowFlags(Qt::Window | Qt::FramelessWindowHint);
    window.showFullScreen();

    return app.exec();
}
