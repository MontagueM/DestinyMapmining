#include <iostream>
#include <fbxsdk.h>
#include "ExportFBX.h"


FbxManager* fbxManager = nullptr;

int ExportFbx(float v[], float f[], wchar_t* name)
{
	std::wcout << "Exporting " << name << " to FBX...\n";
	const char* lFilename = "file.fbx";


	std::wcout << "Done\n";
	return 0;
}

int main()
{
	return 1;
}